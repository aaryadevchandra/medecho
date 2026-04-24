import type { ExtractedJson } from "@/lib/api";

function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-base font-semibold text-blue-800">{title}</h3>
      <div className="mt-3 text-base leading-relaxed text-slate-800">{children}</div>
    </section>
  );
}

function Line({ label, value }: { label: string; value: string }) {
  if (!value.trim()) return null;
  return (
    <p>
      <span className="font-medium text-slate-700">{label}: </span>
      {value}
    </p>
  );
}

export function DocumentSummary({ data }: { data: ExtractedJson }) {
  const pi = data.patient_info;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Your document</h2>
        <p className="mt-1 text-base text-slate-600">
          Plain-language summary from your upload — nothing is shown as raw JSON.
        </p>
      </div>

      <Card title="Patient & visit">
        <Line label="Name" value={pi.name} />
        <Line label="Age" value={pi.age} />
        <Line label="Sex" value={pi.sex} />
        <Line label="Visit date" value={pi.visit_date} />
        <Line label="Doctor" value={pi.doctor_name} />
        {!pi.name.trim() &&
          !pi.age.trim() &&
          !pi.visit_date.trim() &&
          !pi.doctor_name.trim() && (
            <p className="text-slate-500">No patient or visit details were found in the document.</p>
          )}
      </Card>

      <Card title="Diagnoses">
        {data.diagnoses.length ? (
          <ul className="list-inside list-disc space-y-1">
            {data.diagnoses.map((d, i) =>
              String(d).trim() ? <li key={i}>{d}</li> : null
            )}
          </ul>
        ) : (
          <p className="text-slate-500">None listed.</p>
        )}
      </Card>

      <Card title="Medications">
        {data.medications.some((m) => m.name.trim()) ? (
          <ul className="space-y-3">
            {data.medications.map((m, i) =>
              m.name.trim() ? (
                <li key={i} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="font-semibold text-slate-900">{m.name}</p>
                  <Line label="Dose" value={m.dose} />
                  <Line label="Frequency" value={m.frequency} />
                  <Line label="Timing" value={m.timing} />
                  <Line label="Duration" value={m.duration} />
                  <Line label="Warnings" value={m.warnings} />
                </li>
              ) : null
            )}
          </ul>
        ) : (
          <p className="text-slate-500">None listed.</p>
        )}
      </Card>

      <Card title="Tests">
        {data.tests.some((t) => t.test_name.trim()) ? (
          <ul className="space-y-3">
            {data.tests.map((t, i) =>
              t.test_name.trim() ? (
                <li key={i} className="rounded-lg bg-slate-50 px-3 py-2">
                  <p className="font-semibold text-slate-900">{t.test_name}</p>
                  <Line label="Result" value={t.result} />
                  <Line label="Interpretation" value={t.interpretation} />
                </li>
              ) : null
            )}
          </ul>
        ) : (
          <p className="text-slate-500">None listed.</p>
        )}
      </Card>

      <Card title="Instructions">
        {data.doctor_instructions.length ? (
          <ul className="list-inside list-disc space-y-1">
            {data.doctor_instructions.map((d, i) =>
              String(d).trim() ? <li key={i}>{d}</li> : null
            )}
          </ul>
        ) : (
          <p className="text-slate-500">None listed.</p>
        )}
      </Card>

      <Card title="Follow-up">
        {data.follow_up.length ? (
          <ul className="list-inside list-disc space-y-1">
            {data.follow_up.map((d, i) =>
              String(d).trim() ? <li key={i}>{d}</li> : null
            )}
          </ul>
        ) : (
          <p className="text-slate-500">None listed.</p>
        )}
      </Card>

      <Card title="Red flags (from the document)">
        {data.red_flags.length ? (
          <ul className="list-inside list-disc space-y-1 text-red-900">
            {data.red_flags.map((d, i) =>
              String(d).trim() ? <li key={i}>{d}</li> : null
            )}
          </ul>
        ) : (
          <p className="text-slate-500">None listed in the document.</p>
        )}
      </Card>
    </div>
  );
}
