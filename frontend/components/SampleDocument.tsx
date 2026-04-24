const SAMPLE = `Patient Name: John Doe
Age: 52
Sex: Male
Visit Date: 2026-04-24
Doctor: Dr. Sarah Patel

Diagnosis:
- Acute bronchitis

Medications:
1. Azithromycin 500 mg once daily for 3 days after food
2. Paracetamol 500 mg every 6 hours as needed for fever

Tests:
- Chest X-ray: No signs of pneumonia
- CBC: Mildly elevated white blood cell count

Instructions:
- Drink plenty of fluids
- Rest for 3–5 days
- Avoid smoking

Follow-up:
- Follow up with physician in 1 week if symptoms persist

Red Flags:
- Difficulty breathing
- Chest pain
- Fever lasting more than 3 days`;

export function SampleDocument() {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">Sample document format</h2>
      <p className="mt-1 text-base text-slate-600">
        Example discharge-style note — your upload can look similar.
      </p>
      <div className="mt-5 rounded-xl border border-slate-100 bg-slate-50/80 px-6 py-6 shadow-inner">
        <pre className="whitespace-pre-wrap font-mono text-[15px] leading-relaxed text-slate-800">
          {SAMPLE}
        </pre>
      </div>
    </div>
  );
}
