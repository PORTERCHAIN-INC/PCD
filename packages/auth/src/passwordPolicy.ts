/**
 * Password rules shown on customer / merchant signup.
 *
 * Enforcement is Clerk (not Porterchain). Live instance settings:
 * - min_length 0 → Clerk default 8
 * - composition flags off (upper / lower / number / special not individually required)
 * - zxcvbn on, min strength 2 (Fair)
 * - Have I Been Pwned on
 * - allowed_special_characters as below
 *
 * We still list mixed case, a number, and an allowed symbol because that is
 * the reliable way to reach Fair strength. Do not claim a class is required
 * unless Clerk's require_* flags are enabled in the Dashboard.
 */
export const PASSWORD_MIN_LENGTH = 8;

/** Matches Clerk `user_settings.password_settings.allowed_special_characters`. */
export const PASSWORD_ALLOWED_SPECIAL = "!\"#$%&'()*+,-./:;<=>?@[]^_`{|}~";

export const PASSWORD_ALLOWED_SPECIAL_DISPLAY = PASSWORD_ALLOWED_SPECIAL.split("").join(" ");
