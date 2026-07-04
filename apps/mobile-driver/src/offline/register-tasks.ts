import { registerBackgroundGpsTask } from "@porterchain/mobile-offline";
import { createGpsBuffer } from "@porterchain/mobile-storage";

registerBackgroundGpsTask(() => createGpsBuffer("porterchain-driver-offline"));
