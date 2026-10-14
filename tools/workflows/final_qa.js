export const meta = {
  name: 'video-frame-qa',
  description: 'Independent reviewers inspect frames extracted from the assembled video for overlapping/cut-off text, wrong labels and visual glitches',
  phases: [ { title: 'Inspect', detail: 'one reviewer per frame batch' }, { title: 'Consolidate' } ],
}
const ISSUES = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: { frame: { type: 'string' }, severity: { type: 'string', enum: ['block', 'fix', 'nit'] }, what: { type: 'string' } }, required: ['frame', 'severity', 'what'] } } }, required: ['issues'] }
phase('Inspect')
const batches = []
for (let i = 0; i < args.frames.length; i += 6) batches.push(args.frames.slice(i, i + 6))
const found = (await parallel(batches.map((b, k) => () => agent(`You are QA-reviewing frames from a finished 4K video (shown downscaled). The video is a Chinese tech video; its visual language is a dark editorial style with gold accents. For EACH frame listed, use the Read tool to view it and report problems ONLY of these kinds: (a) subtitle (bottom center white text) overlapping other text or UI elements; (b) any text cut off, overflowing its box, or garbled; (c) a label that contradicts the image (e.g. says 云端 for an obviously local label block) or placeholder text like __XX__ or "undefined"/"NaN"/"null"; (d) empty/black panels where an image was clearly expected; (e) obviously broken layout. Do NOT report stylistic preferences. severity: block = must fix before publishing; fix = should fix; nit = cosmetic.
Frames (absolute paths, with the video timestamp in the filename):
${b.map(f => '- ' + f).join('\n')}
Return an empty issues array if all frames are clean.`, { label: `qa:batch${k+1}`, phase: 'Inspect', schema: ISSUES })))).filter(Boolean).flatMap(r => r.issues)
phase('Consolidate')
return { issues: found }
