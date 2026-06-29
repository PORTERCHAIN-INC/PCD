import type { ComponentType } from "react";
import {
  FaFacebook,
  FaInstagram,
  FaLinkedinIn,
  FaWhatsapp,
  FaYoutube,
} from "react-icons/fa6";
import { Rss } from "lucide-react";
import { publicEnv } from "@/lib/env";

export type SocialPlatform =
  | "linkedin"
  | "instagram"
  | "facebook"
  | "youtube"
  | "whatsapp"
  | "blog";

export interface SocialLinkItem {
  platform: SocialPlatform;
  label: string;
  href: string;
  internal?: boolean;
}

export const SOCIAL_LINKS: SocialLinkItem[] = [
  {
    platform: "linkedin",
    label: "LinkedIn",
    href: publicEnv.socialLinkedIn,
  },
  {
    platform: "instagram",
    label: "Instagram",
    href: publicEnv.socialInstagram,
  },
  {
    platform: "facebook",
    label: "Facebook",
    href: publicEnv.socialFacebook,
  },
  {
    platform: "youtube",
    label: "YouTube",
    href: publicEnv.socialYouTube,
  },
  {
    platform: "whatsapp",
    label: "WhatsApp",
    href: publicEnv.socialWhatsApp,
  },
  {
    platform: "blog",
    label: "Blog",
    href: "/blog",
    internal: true,
  },
];

export const SOCIAL_ICONS: Record<SocialPlatform, ComponentType<{ className?: string }>> = {
  linkedin: FaLinkedinIn,
  instagram: FaInstagram,
  facebook: FaFacebook,
  youtube: FaYoutube,
  whatsapp: FaWhatsapp,
  blog: Rss,
};
