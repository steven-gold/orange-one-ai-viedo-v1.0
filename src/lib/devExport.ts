import type { DevCompany } from "./devState";

function csvCell(value: string): string {
  if (/[",\n\r]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

export function devCompaniesCsv(companies: DevCompany[]): string {
  const header = ["名稱", "身分別", "統編", "Email", "電話", "地址", "機會狀態", "壓抑", "佐證"];
  const rows = companies.map((company) => {
    const email = company.contacts.filter((c) => c.type === "EMAIL" && c.status === "ACTIVE").map((c) => c.value).join("、");
    const phone = company.contacts.filter((c) => c.type === "PHONE" && c.status === "ACTIVE").map((c) => c.value).join("、");
    const address = company.contacts.filter((c) => c.type === "ADDRESS" && c.status === "ACTIVE").map((c) => c.value).join("、");
    return [
      company.name,
      company.identityKind,
      company.identityValue,
      email,
      phone,
      address,
      company.opportunity.state,
      company.suppression,
      company.evidence,
    ].map(csvCell).join(",");
  });
  return `\uFEFF${[header.join(","), ...rows].join("\r\n")}`;
}

export function downloadDevCsv(companies: DevCompany[], filename = "dev-database.csv"): void {
  const csv = devCompaniesCsv(companies);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
