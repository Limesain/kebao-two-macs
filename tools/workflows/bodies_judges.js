export const meta = {
  name: 'bodies-judges',
  description: 'Three independent vision judges grade every body/anatomy test image (fingers, limbs, proportions) and a synthesizer writes the verdict JSON',
  phases: [
    { title: 'Grade', detail: '3 judges × 30 images' },
    { title: 'Synthesize', detail: 'majority vote per image + verdict paragraph' },
  ],
}
const ROOT = '/Users/iason/Developer/python-ai-playground/DUAL-MAC-TEST-2026-10'
const GRADE = { type: 'object', properties: { grade: { type: 'string', enum: ['pass', 'minor', 'fail'] }, fingers_ok: { type: 'boolean' }, limbs_ok: { type: 'boolean' }, proportions_ok: { type: 'boolean' }, note: { type: 'string' } }, required: ['grade', 'fingers_ok', 'limbs_ok', 'proportions_ok', 'note'] }
const LENS = ['Count every visible finger on every hand; a wrong count, fused or extra fingers, or a hand merging into an object is a fail. Then check limbs and proportions.',
              'Check whole-body anatomy: number of arms/legs, joint directions, limb lengths and body proportions; interpenetrating or duplicated limbs are a fail. Then check hands.',
              'Judge as a picky photo editor would at 100% zoom: hands, faces in crowds, objects held, strings/needles/balls and how they relate to fingers. Anything a viewer would notice as "AI mistake" is at least minor.']
phase('Grade')
const graded = await pipeline(args.images, async (im, _i, idx) => {
  const votes = (await parallel(LENS.map((lens, j) => () => agent(`You are vision judge #${j+1}. Use the Read tool to view this AI-generated image: ${ROOT}/${im.file}
Theme: ${im.theme_title}. Prompt (Chinese): ${im.prompt}
Grading rules: "pass" = no anatomy/finger/proportion errors visible; "minor" = a small flaw you only notice when looking closely (slightly odd knuckle, soft ambiguity) that a casual viewer would not spot; "fail" = an obvious error (wrong finger count, extra/missing/fused limb, impossible pose, distorted face in a crowd, object merging with a hand).
Lens for this judge: ${lens}
Be concrete in note (e.g. "left hand shows 6 fingers", "right leg bends backward"). Do not grade style or lighting, only anatomy and physical plausibility.`, { label: `grade:${im.name}:${j+1}`, phase: 'Grade', schema: GRADE, model: 'opus' }))))
  return { ...im, votes: votes.filter(Boolean) }
})
log(`graded ${graded.filter(Boolean).length} images`)
phase('Synthesize')
const results = graded.filter(Boolean).map(g => {
  const c = { pass: 0, minor: 0, fail: 0 }; g.votes.forEach(v => c[v.grade]++)
  const grade = c.fail >= 2 ? 'fail' : (c.pass >= 2 ? 'pass' : 'minor')
  return { name: g.name, theme: g.theme, engine: g.engine, grade, votes: c, notes: g.votes.map(v => v.note) }
})
const SUMMARY = { type: 'object', properties: { verdict_zh: { type: 'string' }, narration_zh: { type: 'string' }, highlights: { type: 'array', items: { type: 'string' } } }, required: ['verdict_zh', 'narration_zh', 'highlights'] }
const summary = await agent(`Here are majority-vote anatomy grades for AI images across 5 body/anatomy themes × 6 models (3 local open-source models run on a Mac Studio: zimage=Z-Image Turbo 6B, qwen=Qwen-Image 2.1 ≈7B, krea2=Krea 2 Turbo ≈13B; 3 cloud APIs: seedream, grok, gptimage).
${JSON.stringify(results, null, 1)}
Write (1) verdict_zh: one paragraph in Chinese (≤120 字) for an on-screen card, answering "本地模型能处理好复杂环境和人物躯体了吗" honestly with pass counts per model and the most telling failures; use <em>...</em> around 1-2 key phrases; (2) narration_zh: a spoken Chinese narration of about 90 字, conversational (the narrator is 克宝, an AI that ran the tests), stating how many of the 15 local images passed vs cloud's 15, which local model was best, and one concrete failure example; (3) highlights: up to 4 short Chinese bullet strings.`, { label: 'synthesize', phase: 'Synthesize', schema: SUMMARY, model: 'opus' })
return { results, summary }
