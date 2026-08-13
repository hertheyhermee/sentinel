{{- define "sentinel.name" -}}
{{- default .Chart.Name .Values.appName -}}
{{- end -}}

{{- define "sentinel.labels" -}}
app: {{ .Values.appName | quote }}
app.kubernetes.io/name: {{ include "sentinel.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
