import {
  Dropdown,
  DropdownItem,
  DropdownMenu,
  DropdownSection,
  DropdownTrigger,
} from "@heroui/dropdown";
import { Link } from "@heroui/link";
import {
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  NavbarMenu,
  NavbarMenuItem,
  NavbarMenuToggle,
} from "@heroui/navbar";
import { useNavigate } from "react-router-dom";
import { User } from "@heroui/user";
import { useState } from "react";
import { useTheme } from "@heroui/use-theme";
import { Switch } from "@heroui/switch";

import { LogoIcon, MoonIcon, SunIcon } from "@/components/icons";
import { useAuth } from "@/contexts/AuthContext";
import Footer from "@/components/Footer";

interface DashboardLayoutProps {
  children: React.ReactNode;
  current_root_href?: string;
}

const DashboardLayout = ({
  children,
  current_root_href,
}: DashboardLayoutProps) => {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const { theme, setTheme } = useTheme("dark");

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const toggleTheme = () => {
    setTheme(theme === "light" ? "dark" : "light");
  };

  const menuItems = [
    {
      label: "首页",
      href: "/",
    },
    {
      label: "端点管理",
      href: "/endpoints",
    },
    {
      label: "模型管理",
      href: "/models",
    },
    {
      label: "API 密钥",
      href: "/apikeys",
    },
    {
      label: "主动扫描",
      href: "/fofa",
      adminOnly: true,
    },
    {
      label: "用户管理",
      href: "/users",
      adminOnly: true,
    },
    {
      label: "计划管理",
      href: "/plans",
      adminOnly: true,
    },
  ];

  // 主题切换组件
  const ThemeSwitch = () => (
    <div className="flex items-center gap-2">
      <Switch
        color="primary"
        isSelected={theme === "dark"}
        size="sm"
        thumbIcon={({ isSelected, className }) =>
          isSelected ? (
            <MoonIcon className={className} />
          ) : (
            <SunIcon className={className} />
          )
        }
        onValueChange={toggleTheme}
      />
    </div>
  );

  return (
    <div className="flex flex-col min-h-screen">
      {/* 主内容区域 */}
      <div className="flex-1 flex flex-col overflow-x-hidden overflow-y-auto">
        {/* 导航栏 */}
        <Navbar isBordered onMenuOpenChange={setIsMenuOpen}>
          <NavbarContent>
            <NavbarMenuToggle
              aria-label={isMenuOpen ? "Close menu" : "Open menu"}
              className="sm:hidden"
            />
            <NavbarBrand>
              <LogoIcon className="w-8 h-8" />
              <h2 className="font-bold">Ollama Hack</h2>
            </NavbarBrand>
          </NavbarContent>

          {current_root_href && (
            <NavbarContent className="hidden sm:flex gap-4" justify="center">
              {menuItems.map((item) =>
                item.adminOnly && !isAdmin ? null : (
                  <NavbarItem
                    key={item.href}
                    isActive={item.href === current_root_href}
                  >
                    <Link href={item.href}>
                      <span>{item.label}</span>
                    </Link>
                  </NavbarItem>
                )
              )}
            </NavbarContent>
          )}

          <NavbarContent as="div" justify="end">
            {/* 大屏幕下显示的主题切换开关 */}
            <div className="hidden sm:flex mr-4">
              <ThemeSwitch />
            </div>
            {current_root_href && (
              <Dropdown placement="bottom-end">
                <DropdownTrigger>
                  <User
                    avatarProps={{
                      name: user?.username || "用户",
                    }}
                    description={isAdmin ? "管理员" : "用户"}
                    name={user?.username || "用户"}
                  />
                </DropdownTrigger>
                <DropdownMenu aria-label="用户菜单">
                  <DropdownSection>
                    <DropdownItem key="profile" as={Link} href="/profile">
                      个人资料
                    </DropdownItem>
                    <DropdownItem key="settings" as={Link} href="/settings">
                      设置
                    </DropdownItem>
                    <DropdownItem
                      key="logout"
                      color="danger"
                      onClick={handleLogout}
                    >
                      退出登录
                    </DropdownItem>
                  </DropdownSection>
                </DropdownMenu>
              </Dropdown>
            )}
          </NavbarContent>

          <NavbarMenu>
            {current_root_href
              ? menuItems.map((item) =>
                  item.adminOnly && !isAdmin ? null : (
                    <NavbarMenuItem key={item.href}>
                      <Link
                        color={
                          current_root_href === item.href
                            ? "primary"
                            : "foreground"
                        }
                        href={item.href}
                      >
                        <span>{item.label}</span>
                      </Link>
                    </NavbarMenuItem>
                  )
                )
              : null}
            {/* 小屏幕下显示的主题切换选项 */}
            <NavbarMenuItem className="mt-4 flex justify-center">
              <ThemeSwitch />
            </NavbarMenuItem>
          </NavbarMenu>
        </Navbar>
        <main className="flex-1 p-2 lg:p-8 lg:pl-24 lg:pr-24 md:p-4 md:pl-12 md:pr-12 sm:p-2 sm:pl-8 sm:pr-8">
          {children}
        </main>
        <Footer />
      </div>
    </div>
  );
};

export default DashboardLayout;
