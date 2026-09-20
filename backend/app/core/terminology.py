"""
Canonical user-facing terminology constants for GraphFin.
Prevents over-claiming 'fraud' on unconfirmed statistical anomalies.
"""

# Ground-truth labels & prevalence
POSITIVE = "Positive"
NORMAL = "Normal"
SUSPICIOUS = "Suspicious"
POSITIVE_LABELS = "Positive Labels"
NEGATIVE_LABELS = "Negative Labels"
POSITIVE_PREVALENCE = "Positive Prevalence"

# Confusion matrix row / column headers
ACTUAL_POSITIVE = "Actual Positive"
ACTUAL_NEGATIVE = "Actual Negative"
ACTUAL_NORMAL = "Actual Normal"
PREDICTED_SUSPICIOUS = "Predicted Suspicious"
PREDICTED_NORMAL = "Predicted Normal"
PREDICTED_POSITIVE = "Predicted +"
PREDICTED_NEGATIVE = "Predicted −"

# Cell titles
TP_TITLE = "True Positive (TP)"
FN_TITLE = "False Negative (FN)"
FP_TITLE = "False Positive (FP)"
TN_TITLE = "True Negative (TN)"

# Metric & Stat Card Subtitles
ANOMALIES_DETECTED = "Anomalies detected"
ANOMALIES_MISSED = "Anomalies missed"
FALSE_ALARMS = "False alarms"
NORMAL_CLEARED = "Normal cleared"

# Backward compatibility aliases
LABEL_POSITIVE = POSITIVE
LABEL_ANOMALY_DETECTED = ANOMALIES_DETECTED
LABEL_ANOMALY_MISSED = ANOMALIES_MISSED
LABEL_FALSE_ALARM = FALSE_ALARMS
LABEL_NORMAL_CLEARED = NORMAL_CLEARED
