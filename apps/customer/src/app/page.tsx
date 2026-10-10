import { redirect } from "next/navigation";

/** The portal opens on Send: the one thing customers come to do. */
export default function Home() {
  redirect("/send");
}
