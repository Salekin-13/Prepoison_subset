export const meta = {
  name: 'opt-exec',
  description: 'Prompt optimization: blind Claude executors run one prompt version on the tuning or held-out modules',
  phases: [{ title: 'Execute', detail: 'one executor per module' }],
}
// args: {version, run, modules, split}   split: "tuning" (default) | "heldout"
// tuning  -> inputs traced_inputs_v2/tuning,  outputs assets_opt_<version>_r<run>/_nested
// heldout -> inputs traced_inputs_v2/heldout, outputs assets_opt_heldout_<version>_r<run>/_nested
const R = 'E:/jobs/ff/test/Prepoison_subset'
const { version, run, modules } = args
const split = args.split || 'tuning'
const P = `${R}/assetgen_meta/prompt_opt/${version}/exec_prompt.txt`
const OUT = split === 'tuning' ? `${R}/assets_opt_${version}_r${run}` : `${R}/assets_opt_heldout_${version}_r${run}`
phase('Execute')
const res = await parallel(modules.map(m => () => agent(
  `Use only two files. (1) Read your instructions: ${P} ; read all of it (use several reads with offset and limit). (2) Read the module input: ${R}/assetgen_meta/traced_inputs_v2/${split}/${m}.txt ; read all of it. Do not open any other file, do not search, do not run commands, do not use the web. Follow the instructions and write the final JSON object to ${OUT}/_nested/${m}.json with the Write tool. Then reply DONE.`,
  { label: `${split === 'tuning' ? '' : 'H '}${version} ${m.replace('neorv32_', '')}`, phase: 'Execute' })))
const failed = modules.filter((m, i) => !res[i] || !/DONE/.test(String(res[i])))
log(`${modules.length - failed.length}/${modules.length} executors replied DONE`)
return { version, run, split, failed }
