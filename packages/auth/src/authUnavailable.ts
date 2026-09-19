/**
 * Public copy when sign-in cannot load in a shipped build.
 * No Clerk, env, or command names — those stay on development screens only.
 */
export const signInUnavailableCopy = {
  title: "Sign-in unavailable",
  subtitle: "We cannot sign you in right now. Nothing is wrong with your account.",
  body: "Please try again shortly. If it keeps happening, contact PorterChain and we will sort it out.",
} as const;

export const signUpUnavailableCopy = {
  title: "Sign-up unavailable",
  subtitle: "We cannot create an account right now. Nothing is wrong with your details.",
  body: "Please try again shortly. If it keeps happening, contact PorterChain and we will sort it out.",
} as const;
