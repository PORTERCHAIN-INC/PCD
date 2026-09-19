"use client";

import { useEffect, useState } from "react";

const FORM_FIELD_SELECTOR =
  'input:not([type="hidden"]), textarea, select, [contenteditable="true"]';

function isFormField(element: EventTarget | null | undefined): boolean {
  return element instanceof HTMLElement && Boolean(element.closest(FORM_FIELD_SELECTOR));
}

/** True while any form field on the page has focus (typing). */
export function useFormFieldFocus(): boolean {
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    function syncFromActiveElement() {
      setFocused(isFormField(document.activeElement));
    }

    function onFocusIn(event: FocusEvent) {
      if (isFormField(event.target)) setFocused(true);
    }

    function onFocusOut() {
      requestAnimationFrame(syncFromActiveElement);
    }

    document.addEventListener("focusin", onFocusIn);
    document.addEventListener("focusout", onFocusOut);
    return () => {
      document.removeEventListener("focusin", onFocusIn);
      document.removeEventListener("focusout", onFocusOut);
    };
  }, []);

  return focused;
}
