import asyncio
import datetime
import random
from typing import List, Optional

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete, select
from sqlmodel import col

from src.database import sessionmanager
from src.logging import get_logger
from src.setting.models import SystemSettingKey
from src.setting.service import get_setting
from src.utils import now

from .models import EndpointDB, EndpointTestTask, TaskStatus
from .service import test_and_update_endpoint_and_models

logger = get_logger(__name__)

# Concurrency control semaphore
max_concurrent_tasks = 50
semaphore = asyncio.Semaphore(max_concurrent_tasks)
# Singleton instance
_scheduler_instance = None


# Configure scheduler with limited thread pool executor
def get_scheduler() -> "SchedulerService":
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService()
    return _scheduler_instance


class SchedulerService:
    """
    Service for scheduling and managing endpoint test tasks using APScheduler.
    """

    def __init__(self):
        executors = {
            "default": AsyncIOExecutor(),
            "threadpool": ThreadPoolExecutor(max_workers=20),
        }
        job_defaults = {"coalesce": False, "misfire_grace_time": 30, "max_instances": 1}
        self.scheduler = AsyncIOScheduler(executors=executors, job_defaults=job_defaults)
        self.is_running = False

    async def start(self):
        """
        Initialize the scheduler, recover pending tasks and schedule periodic tasks.
        """
        if self.is_running:
            return

        logger.info("Starting scheduler service...")

        # Recover and schedule
        # await self.recover_pending_tasks()
        # self.scheduler.add_job(
        #     self.recover_pending_tasks,
        #     "date",
        #     id="recover_pending_tasks",
        #     replace_existing=True,
        #     run_date=now() + datetime.timedelta(seconds=5),
        # )
        await self.remove_interupted_tasks()
        await self.schedule_periodic_endpoint_updates(immediate=True)
        self.scheduler.start()
        self.is_running = True
        logger.info("Scheduler service started")

    async def shutdown(self):
        """
        Shutdown the scheduler gracefully.
        """
        if not self.is_running:
            return

        logger.info("Shutting down scheduler service...")
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("Scheduler service shut down")

    async def remove_interupted_tasks(self) -> None:
        """
        Remove all interupted tasks from the database.
        """
        logger.info("Removing interupted tasks...")
        async with sessionmanager.session() as session:
            await session.execute(
                delete(EndpointTestTask).where(
                    col(EndpointTestTask.status).in_([TaskStatus.PENDING, TaskStatus.RUNNING]),
                )
            )
            await session.commit()

    async def recover_pending_tasks(self) -> None:
        """
        Recover all pending or running tasks from the database and reschedule them with throttling.
        """
        logger.info("Recovering pending tasks...")
        async with sessionmanager.session() as session:
            query = select(col(EndpointTestTask.id), col(EndpointTestTask.endpoint_id)).where(
                col(EndpointTestTask.status).in_([TaskStatus.PENDING, TaskStatus.RUNNING]),
                col(EndpointTestTask.scheduled_at) <= now(),
            )
            result = await session.execute(query)
            tasks = result.all()

        logger.info(f"Found {len(tasks)} pending or running tasks to recover")
        # Throttled rescheduling
        for task in tasks:
            if task[0] is not None:
                run_date = now() + datetime.timedelta(seconds=30)
                self.scheduler.add_job(
                    self.run_task,
                    "date",
                    id=f"task_{task[0]}",
                    run_date=run_date,
                    args=[task[0], task[1]],
                    replace_existing=True,
                )
                await asyncio.sleep(0.1)  # small delay to avoid burst

    async def schedule_periodic_endpoint_updates(self, immediate: bool = False):
        """
        Schedule periodic endpoint updates based on system settings.
        """
        logger.info("Scheduling periodic endpoint updates...")
        # Fetch interval setting
        async with sessionmanager.session() as session:
            setting = await get_setting(
                session, SystemSettingKey.UPDATE_ENDPOINT_TASK_INTERVAL_HOURS
            )
            interval_hours = int(setting.value)

        if interval_hours <= 0:
            logger.warning("Update interval is 0, skipping periodic endpoint updates")
            return

        # Remove existing
        if self.scheduler.get_job("periodic_endpoint_updates"):
            self.scheduler.remove_job("periodic_endpoint_updates")

        # Add cron job
        self.scheduler.add_job(
            self.update_all_endpoints,
            "interval",
            hours=interval_hours,
            id="periodic_endpoint_updates",
            replace_existing=True,
            next_run_time=now() + datetime.timedelta(seconds=10) if immediate else None,
        )
        logger.info(f"Scheduled periodic endpoint updates every {interval_hours} hours")

    async def update_all_endpoints(self):
        """
        Update all endpoints by creating and scheduling tasks in batches.
        """
        async with sessionmanager.session() as session:
            interval_hours = await get_setting(
                session, SystemSettingKey.UPDATE_ENDPOINT_TASK_INTERVAL_HOURS
            )
            interval_hours = int(interval_hours.value)

        logger.info("Starting periodic update for all endpoints...")
        async with sessionmanager.session() as session:
            result = await session.execute(select(col(EndpointDB.id)))
            endpoint_ids: List[int | None] = list(result.scalars().all())

        # Randomize endpoint IDs to improve detection rate
        random.shuffle(endpoint_ids)

        logger.info(f"Found {len(endpoint_ids)} endpoints to update")
        batch_size = 500
        count = 0
        for i in range(0, len(endpoint_ids), batch_size):
            batch = endpoint_ids[i : i + batch_size if i + batch_size < len(endpoint_ids) else None]
            tasks_to_schedule = []
            async with sessionmanager.session() as session:
                for endpoint_id in batch:
                    scheduled = now() + datetime.timedelta(seconds=30)
                    if endpoint_id is None:
                        continue

                    # skip if task exists and done in interval
                    q = select(EndpointTestTask).where(
                        col(EndpointTestTask.endpoint_id) == endpoint_id,
                        col(EndpointTestTask.status).in_([TaskStatus.DONE, TaskStatus.RUNNING]),
                        col(EndpointTestTask.scheduled_at)
                        >= scheduled - datetime.timedelta(hours=interval_hours // 2),
                    )
                    res = await session.execute(q)
                    if res.scalars().first() is not None:
                        continue

                    # update if task exists and pending in future
                    q = select(EndpointTestTask).where(
                        col(EndpointTestTask.endpoint_id) == endpoint_id,
                        col(EndpointTestTask.status) == TaskStatus.PENDING,
                        col(EndpointTestTask.scheduled_at) >= scheduled,
                    )
                    res = await session.execute(q)
                    task = res.scalars().first()
                    if task is not None:
                        task.scheduled_at = scheduled
                    else:
                        task = EndpointTestTask(endpoint_id=endpoint_id, scheduled_at=scheduled)
                    # task = EndpointTestTask(endpoint_id=endpoint_id, scheduled_at=scheduled)
                    session.add(task)
                    await session.commit()
                    await session.refresh(task)
                    tasks_to_schedule.append((task.id, endpoint_id, scheduled))
                await session.commit()

            for task_id, eid, run_date in tasks_to_schedule:
                self.scheduler.add_job(
                    self.run_task,
                    "date",
                    id=f"task_{task_id}",
                    run_date=run_date,
                    args=[task_id, eid],
                    replace_existing=True,
                )
            count += batch_size
            if count > len(endpoint_ids):
                count = len(endpoint_ids)
            logger.info(
                f"Scheduled {len(tasks_to_schedule)} tasks ({count}/{len(endpoint_ids)} {count/len(endpoint_ids)*100:.2f}%)"
            )
            await asyncio.sleep(2)

    async def schedule_endpoint_test(
        self, endpoint_id: int, run_date: Optional[datetime.datetime] = None
    ) -> Optional[EndpointTestTask]:
        logger.debug(f"Scheduling single test for {endpoint_id}")
        if run_date is None:
            run_date = now() + datetime.timedelta(seconds=5)

        async with sessionmanager.session() as session:
            ep = (
                (await session.execute(select(EndpointDB).where(col(EndpointDB.id) == endpoint_id)))
                .scalars()
                .first()
            )
            if not ep:
                logger.error("Endpoint not found")
                return None

            # skip if task exists and is running in 10 min
            res = await session.execute(
                select(EndpointTestTask).where(
                    col(EndpointTestTask.endpoint_id) == endpoint_id,
                    col(EndpointTestTask.status) == TaskStatus.RUNNING,
                    col(EndpointTestTask.scheduled_at) >= now() - datetime.timedelta(minutes=10),
                )
            )
            if res.scalars().first() is not None:
                logger.debug("Existing running task, skip")
                return None

            # check if task exists and pending in future
            res = await session.execute(
                select(EndpointTestTask).where(
                    col(EndpointTestTask.endpoint_id) == endpoint_id,
                    col(EndpointTestTask.status) == TaskStatus.PENDING,
                    col(EndpointTestTask.scheduled_at) >= run_date,
                )
            )
            task = res.scalars().first()
            if task is not None:
                logger.debug("Existing later task, update it")
                task.scheduled_at = run_date
            else:
                task = EndpointTestTask(endpoint_id=endpoint_id, scheduled_at=run_date)
            session.add(task)
            await session.commit()
            await session.refresh(task)

        self.scheduler.add_job(
            self.run_task,
            "date",
            id=f"task_{task.id}",
            run_date=run_date,
            args=[task.id, endpoint_id],
            replace_existing=True,
        )
        return task

    async def run_task(self, task_id: int, endpoint_id: int):
        """
        Run a single endpoint test task with concurrency control and safe session handling.
        """
        async with semaphore:
            logger.debug(f"Running task {task_id} for endpoint {endpoint_id}")
            async with sessionmanager.session() as session:
                task = await session.get(EndpointTestTask, task_id)
                if not task or task.status == TaskStatus.DONE:
                    return
                task.status = TaskStatus.RUNNING
                task.last_tried = now()
                await session.commit()

            try:
                await test_and_update_endpoint_and_models(endpoint_id)
                async with sessionmanager.session() as session:
                    async with session.begin():
                        task = await session.get(EndpointTestTask, task_id)
                        if task:
                            task.status = TaskStatus.DONE
                logger.debug(f"Task {task_id} completed successfully")
            except Exception as e:
                logger.error(f"Error running task {task_id}: {e}")
                async with sessionmanager.session() as session:
                    async with session.begin():
                        task = await session.get(EndpointTestTask, task_id)
                        if task:
                            task.status = TaskStatus.FAILED
                logger.error(f"Task {task_id} marked as FAILED")
