type MessageTranslator = (key: string) => string;

export function collectFaqItems(
  t: MessageTranslator,
  prefix: string,
  count: number
): { question: string; answer: string }[] {
  return Array.from({ length: count }, (_, i) => ({
    question: t(`${prefix}.${i}.q`),
    answer: t(`${prefix}.${i}.a`),
  }));
}

export function collectTimelineSteps(
  t: MessageTranslator,
  prefix: string,
  count: number
): { title: string; description: string }[] {
  return Array.from({ length: count }, (_, i) => ({
    title: t(`${prefix}.${i}.title`),
    description: t(`${prefix}.${i}.description`),
  }));
}

export function collectResourceItems(
  t: MessageTranslator,
  prefix: string,
  count: number
): { title: string; description: string; href: string }[] {
  return Array.from({ length: count }, (_, i) => ({
    title: t(`${prefix}.${i}.title`),
    description: t(`${prefix}.${i}.description`),
    href: t(`${prefix}.${i}.href`),
  }));
}

export function collectCardItems(
  t: MessageTranslator,
  prefix: string,
  count: number,
  ids?: string[],
  includeDetail = false
): { title: string; description: string; id?: string; detail?: string }[] {
  return Array.from({ length: count }, (_, i) => ({
    title: t(`${prefix}.${i}.title`),
    description: t(`${prefix}.${i}.description`),
    ...(ids?.[i] ? { id: ids[i] } : {}),
    ...(includeDetail ? { detail: t(`${prefix}.${i}.detail`) } : {}),
  }));
}
