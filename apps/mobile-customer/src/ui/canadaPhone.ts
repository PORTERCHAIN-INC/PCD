/** Display a Canadian number as +1 xxx-xxx-xxxx while the customer types. */
export function formatCanadianPhone(input: string): string {
  let digits = input.replace(/\D/g, "");
  if (digits.startsWith("1")) digits = digits.slice(1);
  digits = digits.slice(0, 10);
  if (!digits) return "";
  const area = digits.slice(0, 3);
  const prefix = digits.slice(3, 6);
  const line = digits.slice(6, 10);
  if (digits.length <= 3) return `+1 ${area}`;
  if (digits.length <= 6) return `+1 ${area}-${prefix}`;
  return `+1 ${area}-${prefix}-${line}`;
}
