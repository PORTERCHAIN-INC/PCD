import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

const navigation = createNavigation(routing);

export const BaseLink = navigation.Link;
export const { redirect, usePathname, useRouter, getPathname } = navigation;
