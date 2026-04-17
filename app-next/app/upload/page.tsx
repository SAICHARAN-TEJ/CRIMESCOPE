'use client';
// app/upload/page.tsx — Two-step seed intake
import { useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, FileText, X, CheckCircle, AlertCircle, ChevronRight } from 'lucide-react';
import { DataPanel }    from '@/components/ui/DataPanel';
import { ProgressBeam } from '@/components/ui/ProgressBeam';
import { cn }           from '@/lib/utils';
import * as api         from '@/lib/api';

type Step = 'files' | 'scenario' | 'processing';

interface FileEntry {
  file: File;
  id:   string;
  status: 'pending' | 'parsing' | 'done' | 'error';
  chars?: number;
}

const DEPTH_OPTIONS = [
  { value: 'surface', label: 'SURFACE SCAN',   desc: '50 rounds — fast overview',     color: '#00BCD4' },
  { value: 'deep',    label: 'DEEP TRACE',     desc: '150 rounds — standard analysis', color: '#F57F17' },
  { value: 'full',    label: 'FULL IMMERSION', desc: '300 rounds — maximum fidelity',  color: '#C62828' },
];

const JURISDICTIONS = [
  'Metro PD District 1', 'Metro PD District 4', 'Gang Crimes Division',
  'Financial Crimes Unit', 'Narcotics Division', 'Homicide Bureau',
  'Organized Crime Task Force', 'Federal — FBI',
];

export default function UploadPage() {
  const router    = useRouter();
  const [step, setStep]           = useState<Step>('files');
  const [files, setFiles]         = useState<FileEntry[]>([]);
  const [dragOver, setDragOver]   = useState(false);
  const [scenario, setScenario]   = useState('');
  const [depth, setDepth]         = useState('deep');
  const [jurisdiction, setJurisdiction] = useState('Metro PD District 4');
  const [progress, setProgress]   = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [error, setError]         = useState('');
  const dropRef = useRef<HTMLDivElement>(null);

  const allowed = ['pdf', 'docx', 'doc', 'txt', 'csv', 'md'];

  const addFiles = useCallback((incoming: File[]) => {
    const valid = incoming.filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase();
      return ext && allowed.includes(ext);
    });
    setFiles(prev => [
      ...prev,
      ...valid.map(f => ({ file: f, id: crypto.randomUUID(), status: 'pending' as const })),
    ]);
  }, [allowed]);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(Array.from(e.dataTransfer.files));
  };

  const removeFile = (id: string) => setFiles(f => f.filter(x => x.id !== id));

  const handleSubmit = async () => {
    if (!scenario.trim() || files.length === 0) return;
    setStep('processing');
    setError('');
    try {
      setStatusMsg('CREATING PROJECT...');
      setProgress(10);
      const proj: Record<string, string> = await api.createProject(
        `[${depth.toUpperCase()}] ${scenario.slice(0, 60)}`,
        scenario
      ) as Record<string, string>;
      const projectId = proj.project_id;

      setStatusMsg('UPLOADING DOCUMENTS...');
      setProgress(30);
      await api.uploadFiles(projectId, files.map(f => f.file));

      setStatusMsg('GENERATING CRIME ONTOLOGY...');
      setProgress(55);
      const ontRes: { task_id?: string } = await api.generateOntology(projectId, scenario) as { task_id?: string };

      setStatusMsg('BUILDING INTELLIGENCE GRAPH...');
      setProgress(75);
      await api.buildGraph(projectId);

      setProgress(100);
      setStatusMsg('ANALYSIS INITIATED — BUILDING INTELLIGENCE GRAPH');

      setTimeout(() => router.push(`/graph/${projectId}`), 1200);
    } catch (err) {
      setError(String(err));
      setStep('scenario');
    }
  };

  const fmtSize = (b: number) => b > 1e6 ? `${(b / 1e6).toFixed(1)}MB` : `${(b / 1e3).toFixed(0)}KB`;

  return (
    <div className="min-h-full bg-[#080A0F] bg-grid p-5">
      <div className="max-w-3xl mx-auto">

        {/* Header */}
        <div className="mb-8">
          <div className="font-terminal text-[9px] tracking-[5px] text-[#455A64] mb-1">NEW ANALYSIS</div>
          <h1 className="font-terminal text-[22px] tracking-wider text-[#E8EAED]">SEED INTAKE PIPELINE</h1>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-3 mb-8">
          {(['files', 'scenario'] as const).map((s, i) => (
            <div key={s} className="flex items-center gap-3">
              <div className={cn(
                'flex items-center gap-2 font-terminal text-[9px] tracking-widest px-3 py-1.5 border',
                step === s || (step === 'processing' && i === 1)
                  ? 'border-[#00BCD4] text-[#00BCD4] bg-[#00BCD4]/10'
                  : files.length > 0 && s === 'files'
                  ? 'border-[#2E7D32] text-[#2E7D32]'
                  : 'border-[#1E2A38] text-[#455A64]',
              )}>
                <span>{i + 1}</span>
                <span>{s === 'files' ? 'DOCUMENTS' : 'SCENARIO BRIEF'}</span>
              </div>
              {i === 0 && <ChevronRight className="w-3 h-3 text-[#1E2A38]" />}
            </div>
          ))}
        </div>

        {error && (
          <div className="flex items-center gap-3 px-4 py-3 mb-4 border border-[#C62828]/40 bg-[#C62828]/10 font-code text-[11px] text-[#C62828]">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {/* ── STEP 1: FILES ── */}
        {step === 'files' && (
          <DataPanel title="UPLOAD DOCUMENTS" className="mb-4">
            {/* Drop zone */}
            <div
              ref={dropRef}
              onDrop={onDrop}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              className={cn(
                'border-2 border-dashed rounded-sm p-10 text-center transition-all cursor-pointer mb-5',
                dragOver ? 'border-[#00BCD4] bg-[#00BCD4]/10' : 'border-[#1E2A38] hover:border-[#37474F]',
              )}
              onClick={() => document.getElementById('file-input')?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && document.getElementById('file-input')?.click()}
              aria-label="Drop files here or click to browse"
            >
              <input
                id="file-input"
                type="file"
                className="sr-only"
                multiple
                accept=".pdf,.docx,.doc,.txt,.csv,.md"
                onChange={e => addFiles(Array.from(e.target.files ?? []))}
              />
              <Upload className="w-8 h-8 text-[#37474F] mx-auto mb-3" aria-hidden="true" />
              <p className="font-terminal text-[12px] tracking-widest text-[#455A64] mb-1">
                DROP FILES HERE
              </p>
              <p className="font-code text-[10px] text-[#1E2A38]">PDF · DOCX · TXT · CSV · MD</p>
            </div>

            {/* File list */}
            {files.length > 0 && (
              <div className="space-y-2 mb-5">
                {files.map(f => (
                  <div key={f.id} className="flex items-center gap-3 px-3 py-2.5 bg-[#0D1117] border border-[#1E2A38]">
                    <FileText className="w-4 h-4 text-[#00BCD4] shrink-0" aria-hidden="true" />
                    <div className="flex-1 min-w-0">
                      <div className="font-code text-[11px] text-[#E8EAED] truncate">{f.file.name}</div>
                      <div className="font-code text-[9px] text-[#455A64]">{fmtSize(f.file.size)}</div>
                    </div>
                    <button
                      onClick={() => removeFile(f.id)}
                      className="text-[#37474F] hover:text-[#C62828] transition-colors"
                      aria-label={`Remove ${f.file.name}`}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                    {f.status === 'done' && <CheckCircle className="w-3.5 h-3.5 text-[#2E7D32]" />}
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => setStep('scenario')}
              disabled={files.length === 0}
              className={cn(
                'w-full py-3 font-terminal text-[12px] tracking-[4px] border transition-all',
                files.length > 0
                  ? 'border-[#00BCD4] text-[#00BCD4] bg-[#00BCD4]/5 hover:bg-[#00BCD4]/15 clip-tactical'
                  : 'border-[#1E2A38] text-[#37474F] cursor-not-allowed',
              )}
              aria-disabled={files.length === 0}
            >
              CONTINUE → SCENARIO BRIEF
            </button>
          </DataPanel>
        )}

        {/* ── STEP 2: SCENARIO ── */}
        {step === 'scenario' && (
          <DataPanel title="SCENARIO BRIEF" className="mb-4">
            <div className="mb-5">
              <label className="block font-terminal text-[9px] tracking-widest text-[#455A64] mb-2">
                PREDICTION SCENARIO
              </label>
              <textarea
                value={scenario}
                onChange={e => setScenario(e.target.value)}
                rows={6}
                placeholder="Describe the crime scenario for simulation analysis. Be specific about geography, entities, and the behavioral outcomes you want to predict..."
                className="w-full bg-[#0D1117] border border-[#1E2A38] text-[#E8EAED] font-code text-[12px] p-4 resize-none leading-relaxed placeholder:text-[#1E2A38] focus:outline-none focus:border-[#00BCD4] transition-colors"
              />
            </div>

            <div className="mb-5">
              <label className="block font-terminal text-[9px] tracking-widest text-[#455A64] mb-2">
                SIMULATION DEPTH
              </label>
              <div className="grid grid-cols-3 gap-2">
                {DEPTH_OPTIONS.map(d => (
                  <button
                    key={d.value}
                    onClick={() => setDepth(d.value)}
                    className={cn(
                      'p-3 border text-left transition-all',
                      depth === d.value
                        ? 'border-[#00BCD4] bg-[#00BCD4]/10'
                        : 'border-[#1E2A38] hover:border-[#37474F]',
                    )}
                  >
                    <div className="font-terminal text-[9px] tracking-widest mb-1" style={{ color: d.color }}>
                      {d.label}
                    </div>
                    <div className="font-code text-[9px] text-[#455A64]">{d.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-6">
              <label className="block font-terminal text-[9px] tracking-widest text-[#455A64] mb-2">
                JURISDICTION
              </label>
              <select
                value={jurisdiction}
                onChange={e => setJurisdiction(e.target.value)}
                className="w-full bg-[#0D1117] border border-[#1E2A38] text-[#E8EAED] font-code text-[11px] px-3 py-2 focus:outline-none focus:border-[#00BCD4] transition-colors"
              >
                {JURISDICTIONS.map(j => (
                  <option key={j} value={j} className="bg-[#0D1117]">{j}</option>
                ))}
              </select>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep('files')}
                className="px-5 py-3 border border-[#1E2A38] text-[#455A64] font-terminal text-[11px] tracking-widest hover:border-[#37474F] transition-all"
              >
                ← BACK
              </button>
              <button
                onClick={handleSubmit}
                disabled={!scenario.trim()}
                className={cn(
                  'flex-1 py-3 font-terminal text-[12px] tracking-[4px] border transition-all clip-tactical',
                  scenario.trim()
                    ? 'border-[#C62828] text-[#C62828] bg-[#C62828]/5 hover:bg-[#C62828]/15'
                    : 'border-[#1E2A38] text-[#37474F] cursor-not-allowed',
                )}
                aria-disabled={!scenario.trim()}
              >
                INITIATE ANALYSIS
              </button>
            </div>
          </DataPanel>
        )}

        {/* ── STEP 3: PROCESSING ── */}
        {step === 'processing' && (
          <DataPanel title="ANALYSIS INITIATED">
            <div className="py-8 text-center">
              <div className="font-terminal text-[14px] tracking-[4px] text-[#00BCD4] mb-6">
                {statusMsg}
              </div>
              <div className="mb-6">
                <ProgressBeam phase={Math.floor(progress / 25)} active label={`${progress}%`} />
              </div>
              <div className="font-code text-[10px] text-[#455A64]">
                BUILDING INTELLIGENCE GRAPH — PLEASE WAIT
              </div>
            </div>
          </DataPanel>
        )}
      </div>
    </div>
  );
}
