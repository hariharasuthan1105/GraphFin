/**
 * Canonical user-facing terminology constants for GraphFin.
 * Prevents over-claiming "fraud" on unconfirmed statistical anomalies.
 */

export const TERMINOLOGY = {
  // Ground-truth labels & prevalence
  POSITIVE: "Positive",
  NORMAL: "Normal",
  SUSPICIOUS: "Suspicious",
  POSITIVE_LABELS: "Positive Labels",
  NEGATIVE_LABELS: "Negative Labels",
  POSITIVE_PREVALENCE: "Positive Prevalence",

  // Confusion matrix row / column headers
  ACTUAL_POSITIVE: "Actual Positive",
  ACTUAL_NEGATIVE: "Actual Negative",
  ACTUAL_NORMAL: "Actual Normal",
  PREDICTED_SUSPICIOUS: "Predicted Suspicious",
  PREDICTED_NORMAL: "Predicted Normal",
  PREDICTED_POSITIVE: "Predicted +",
  PREDICTED_NEGATIVE: "Predicted −",

  // Cell titles
  TP_TITLE: "True Positive (TP)",
  FN_TITLE: "False Negative (FN)",
  FP_TITLE: "False Positive (FP)",
  TN_TITLE: "True Negative (TN)",

  // Deep-dive & Confusion matrix stat card subtitles
  ANOMALIES_DETECTED: "Anomalies detected",
  ANOMALIES_MISSED: "Anomalies missed",
  FALSE_ALARMS: "False alarms",
  NORMAL_CLEARED: "Normal cleared",

  // Abbreviations
  TP: "TP",
  FP: "FP",
  TN: "TN",
  FN: "FN",
} as const;

export const LABEL_POSITIVE = TERMINOLOGY.POSITIVE;
export const LABEL_ANOMALY_DETECTED = TERMINOLOGY.ANOMALIES_DETECTED;
export const LABEL_ANOMALY_MISSED = TERMINOLOGY.ANOMALIES_MISSED;
export const LABEL_FALSE_ALARM = TERMINOLOGY.FALSE_ALARMS;
export const LABEL_NORMAL_CLEARED = TERMINOLOGY.NORMAL_CLEARED;
