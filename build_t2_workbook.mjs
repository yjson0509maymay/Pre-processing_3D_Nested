import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "C:/Users/asia/Documents/파이널/outputs/t2_303_unique_subjects";
const fullCsv = await fs.readFile(`${outputDir}/T2_download_list_303_unique_subjects.csv`, "utf8");
const subjectCsv = await fs.readFile(`${outputDir}/T2_subject_numbers_303.csv`, "utf8");

const workbook = await Workbook.fromCSV(fullCsv, { sheetName: "Download_List_303" });
const downloadSheet = workbook.worksheets.getItem("Download_List_303");
const subjectBook = await Workbook.fromCSV(subjectCsv, { sheetName: "Subject_Numbers" });
const subjectValues = subjectBook.worksheets.getItem("Subject_Numbers").getUsedRange().values;
const subjectSheet = workbook.worksheets.add("Subject_Numbers");
subjectSheet.getRangeByIndexes(0, 0, subjectValues.length, subjectValues[0].length).values = subjectValues;

const summary = workbook.worksheets.add("Summary");
summary.getRange("A1:E1").merge();
summary.getRange("A1").values = [["T2 Download Cohort: 303 Unique Subjects"]];
summary.getRange("A3:B9").values = [
  ["Metric", "Count"],
  ["Selected rows", 303],
  ["Unique subjects", 303],
  ["Unique Image Data IDs", 303],
  ["Control", 110],
  ["Prodromal", 58],
  ["PD", 135],
];
summary.getRange("D3:E5").values = [
  ["Selection source", "Count"],
  ["Reference subjects retained", 235],
  ["New subjects added", 68],
];
summary.getRange("A11:E16").values = [
  ["Selection rule", "Details", "", "", ""],
  ["Included", "MRI / Original; Description contains T2, PD-T2, dual TSE, double TSE, or AX DE TSE", "", "", ""],
  ["Excluded", "FLAIR, T2*, T2_STAR, REPEAT, RPT, and MPR-derived series", "", "", ""],
  ["Representative series", "Previously downloaded Image ID first, then reference subject, BL visit, and standard PD-T2 sequence", "", "", ""],
  ["Cohort target", "Control 110 + Prodromal 58 + PD 135", "", "", ""],
  ["Important", "This is a proposed download cohort; verify sequence suitability/QC after downloading.", "", "", ""],
];

summary.getRange("A1:E1").format = { fill: "#17324D", font: { bold: true, color: "#FFFFFF", size: 16 }, verticalAlignment: "center" };
summary.getRange("A3:B3").format = { fill: "#2E6F73", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("D3:E3").format = { fill: "#A34A28", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A11:E11").format = { fill: "#2E6F73", font: { bold: true, color: "#FFFFFF" } };
for (const range of ["A3:B9", "D3:E5", "A11:E16"]) {
  summary.getRange(range).format.borders = { preset: "all", style: "thin", color: "#D4DCE3" };
}
summary.getRange("A11:A16").format.font = { bold: true };
summary.getRange("A12:E16").format.wrapText = true;
summary.getRange("A:A").format.columnWidth = 24;
summary.getRange("B:B").format.columnWidth = 70;
summary.getRange("C:C").format.columnWidth = 3;
summary.getRange("D:D").format.columnWidth = 30;
summary.getRange("E:E").format.columnWidth = 16;
summary.getRange("A1:E1").format.rowHeight = 28;
summary.showGridLines = false;

downloadSheet.freezePanes.freezeRows(1);
subjectSheet.freezePanes.freezeRows(1);
for (const sheet of [downloadSheet, subjectSheet]) {
  sheet.getUsedRange().getRow(0).format = { fill: "#17324D", font: { bold: true, color: "#FFFFFF" }, wrapText: true };
  sheet.getUsedRange().format.borders = { preset: "inside", style: "thin", color: "#E5E7EB" };
}
downloadSheet.getRange("A:A").format.columnWidth = 16;
downloadSheet.getRange("B:C").format.columnWidth = 13;
downloadSheet.getRange("D:F").format.columnWidth = 11;
downloadSheet.getRange("G:G").format.columnWidth = 34;
downloadSheet.getRange("H:J").format.columnWidth = 14;
downloadSheet.getRange("K:N").format.columnWidth = 24;
subjectSheet.getRange("A:B").format.columnWidth = 13;
subjectSheet.getRange("C:C").format.columnWidth = 16;
subjectSheet.getRange("D:D").format.columnWidth = 10;
subjectSheet.getRange("E:E").format.columnWidth = 34;
subjectSheet.getRange("F:G").format.columnWidth = 24;

downloadSheet.tables.add(downloadSheet.getUsedRange(), true, "DownloadList303");
subjectSheet.tables.add(subjectSheet.getUsedRange(), true, "SubjectNumbers303");

const preview = await workbook.render({ sheetName: "Summary", range: "A1:E16", scale: 1.5, format: "png" });
await fs.writeFile(`${outputDir}/summary_preview.png`, new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(`${outputDir}/T2_download_cohort_303_unique_subjects.xlsx`);

const verification = await workbook.inspect({
  kind: "table",
  range: "Summary!A1:E16",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 6,
});
console.log(verification.ndjson);
