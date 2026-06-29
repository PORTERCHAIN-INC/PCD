import { careerPositions, type CareerDepartment } from "@/data/careers";

export interface PositionData {
  id: string;
  department: CareerDepartment;
  title: string;
  location: string;
  employmentType: string;
  experience: string;
  description: string;
  applyLabel: string;
}

export function buildPositionsFromTranslations(
  t: (key: string) => string
): PositionData[] {
  return careerPositions.map(({ id, department }) => ({
    id,
    department,
    title: t(`${id}.title`),
    location: t(`${id}.location`),
    employmentType: t(`${id}.employmentType`),
    experience: t(`${id}.experience`),
    description: t(`${id}.description`),
    applyLabel: t("apply"),
  }));
}
