import { SVGProps } from "react";
import { FontAwesomeIconProps as FontAwesomeIconPropsType } from "@fortawesome/react-fontawesome";
export type IconSvgProps = SVGProps<SVGSVGElement> & {
  size?: number;
};

// remove icon prop
export type FontAwesomeIconProps = Omit<FontAwesomeIconPropsType, "icon">;

// 导出所有类型
export * from "./common";
export * from "./auth";
export * from "./endpoint";
export * from "./model";
export * from "./apikey";
export * from "./plan";
export * from "./setting";
export * from "./fofa";
export * from "./subscription";
