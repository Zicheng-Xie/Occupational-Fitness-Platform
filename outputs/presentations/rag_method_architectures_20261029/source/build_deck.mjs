/**
 * Code-grounded architecture figures. Reference: supplied PDF, page 4, style only.
 * All labels and computational edges come from the source files named in notes.
 * The generated raster concept is not embedded; every final object is native.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import os from 'node:os';
import {pathToFileURL} from 'node:url';

const project = path.resolve(process.env.PROJECT_ROOT || process.cwd());
const work = path.join(project,'outputs/presentations/rag_method_architectures_20261029');
const runtime = process.env.CODEX_PRIMARY_RUNTIME || path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies');
process.env.RUNTIME_NODE_MODULES ||= path.join(runtime,'node/node_modules');
const skill = process.env.PRESENTATIONS_SKILL_DIR || path.join(os.homedir(),'.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations');
const {Presentation, PresentationFile} = await import(pathToFileURL(path.join(runtime,'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const {finalizePresentation} = await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const C = {navy:'#071C35',ink:'#10253F',teal:'#13A6A6',cyan:'#46B1E1',pale:'#DFF7F5',blue:'#4E95D9',orange:'#EE945E',peach:'#F6C6AD',cream:'#FFF2D8',grey:'#EAF0F6',arrow:'#D8E1EA',outline:'#104862',white:'#FFFFFF'};
const W=1280,H=720, deck=Presentation.create({slideSize:{width:W,height:H}});
const inventory=[];
for(const dir of ['build','output','output/figures']) await fs.mkdir(path.join(work,dir),{recursive:true});

function rect(s,name,x,y,w,h,fill=C.white,stroke='none',sw=0){
 const z=s.shapes.add({name,geometry:'rect',position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:sw,style:'solid'}});
 return z;
}
function text(s,name,value,x,y,w,h,size=22,color=C.ink,align='center',bold=true){
 const z=rect(s,name,x,y,w,h,'none');z.text=value;
 z.text.style={typeface:'Calibri',fontSize:size,bold,color,alignment:align,verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:3};
 return z;
}
function box(s,name,value,x,y,w,h,fill=C.cyan,color=C.white,size=22){
 const z=rect(s,name,x,y,w,h,fill);z.text=value;
 z.text.style={typeface:'Calibri',fontSize:size,bold:true,color,alignment:'center',verticalAlignment:'middle',autoFit:'none',wrap:'square',insets:7};return z;
}
function frame(s,name,title,x,y,w,h){
 const z=rect(s,name,x,y,w,h,C.white,C.outline,1.7);
 const labelW=Math.min(w-32,Math.max(200,title.length*11.8+36));
 rect(s,name+'-heading-mask',x+(w-labelW)/2,y-14,labelW,31,C.white);
 text(s,name+'-heading',title,x+(w-labelW)/2,y-17,labelW,33,22);
 return z;
}
function panel(s,name,title,x,y,w,h,fill=C.teal){
 const z=rect(s,name,x,y,w,h,fill);text(s,name+'-label',title,x+8,y+6,w-16,35,22,fill===C.pale?C.ink:C.white);return z;
}
function arrow(s,name,x1,y1,x2,y2,color=C.arrow,width=9){
 if(Math.abs(y2-y1)<.01){
  const right=x2>x1;return s.shapes.add({name,geometry:right?'rightArrow':'leftArrow',position:{left:Math.min(x1,x2),top:y1-14,width:Math.abs(x2-x1),height:28},fill:color,line:{fill:'none',width:0}});
 }
 if(Math.abs(x2-x1)<.01){
  return s.shapes.add({name,geometry:y2>y1?'downArrow':'upArrow',position:{left:x1-14,top:Math.min(y1,y2),width:28,height:Math.abs(y2-y1)},fill:color,line:{fill:'none',width:0}});
 }
 return poly(s,name,[[x1,y1],[x2,y1],[x2,y2]],color,width);
}
function poly(s,name,points,color=C.arrow,width=8){
 const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);const x=Math.min(...xs),y=Math.min(...ys),w=Math.max(1,Math.max(...xs)-x),h=Math.max(1,Math.max(...ys)-y);
 const commands=points.map((p,i)=>i?{lineTo:{x:p[0]-x,y:p[1]-y}}:{moveTo:{x:p[0]-x,y:p[1]-y}});
 const z=s.shapes.add({name,geometry:'custom',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width,style:'solid'},customPaths:[{width:w,height:h,commands}]});
 const a=points.at(-2),b=points.at(-1),dx=b[0]-a[0],dy=b[1]-a[1];
 const rotation=Math.abs(dx)>Math.abs(dy)?(dx>0?90:270):(dy>0?180:0);
 const cx=b[0]-(Math.abs(dx)>Math.abs(dy)?Math.sign(dx)*8:0),cy=b[1]-(Math.abs(dy)>=Math.abs(dx)?Math.sign(dy)*8:0);
 s.shapes.add({name:name+'-arrowhead',geometry:'triangle',position:{left:cx-11,top:cy-11,width:22,height:22,rotation},fill:color,line:{fill:'none',width:0}});return z;
}
function header(name,method,kind,title,caption,sources,notes=''){
 const s=deck.slides.add();s.background.fill=C.white;
 text(s,'product','Occupational Fitness Platform',54,20,700,28,15,C.teal,'left');
 text(s,'title',title,54,59,1168,52,32,'#000000','left');
 text(s,'diagram-kind',kind,55,110,1160,35,23,C.ink,'left');
 text(s,'page',String(deck.slides.items.length).padStart(2,'0'),1190,22,40,26,15,C.teal,'right');
 if(caption) text(s,'caption',caption,54,653,1170,51,17,C.ink,'left',false);
 s.speakerNotes.text=[
  `Diagram: ${title} / ${kind}. Method ${method}.`,
  'Visual reference: supplied Framework PDF, page 4 only. Only palette, Calibri bold, sharp rectangular grouping, outlined support frames and pale grey arrows were borrowed. None of its system content, names or topology were used.',
  'Scientific content: inspected first-party source code and frozen actual experiment records. Production defaults and earlier methods are unchanged.',
  ...sources.map(p=>'Code: '+p),notes
 ].filter(Boolean).join('\n\n');
 inventory.push({name,method,kind,title,sources});return s;
}
function extension(s,{baselineX=1110,baselineBottom=460,inputX=145,inputBottom=440,inputPoints=null,replay=false}={}){
 panel(s,'refinement-layer','Latest experimental refinement',300,550,600,89,C.teal);
 box(s,'literal-views','Literal views\n+ weighted RRF',312,588,176,43,C.orange,C.white,18);
 box(s,'literal-parents','Verified original\nparent passages',508,588,176,43,C.orange,C.white,18);
 box(s,'protected-allocation','Protect prefixes\n1 / 3 / 5 / 10',704,588,184,43,C.orange,C.white,18);
 arrow(s,'refine-view-to-parent',488,609,508,609);arrow(s,'refine-parent-to-protection',684,609,704,609);
 box(s,'refined-output','Refined Top 10\noriginal passages',1000,566,225,65,C.navy,C.white,21);
 arrow(s,'refined-original-output',900,600,1000,600);
 poly(s,'baseline-to-refinement',[[baselineX,baselineBottom],[baselineX,510],[600,510],[600,550]]);
 poly(s,'note-to-literal-context',inputPoints||[[inputX,inputBottom],[inputX,610],[300,610]]);
 if(replay) text(s,'replay-status','Frozen native candidates replayed',705,638,520,22,15,C.outline,'right',false);
}
function flowBox(s,name,value,x,y,w=200,fill=C.cyan,size=21,h=106){return box(s,name,value,x,y,w,h,fill,fill===C.grey||fill===C.cream||fill===C.pale?C.ink:C.white,size);}
function commonFlowBottom(s,lastX=1140){
 arrow(s,'core-to-refinement',lastX,296,lastX,430);
 const xs=[1050,800,550,300,50],ws=[180,200,200,200,200];
 const labels=['Baseline + wider\nmeasured frontier','Verbatim sentence\nretrieval views','Weighted RRF\n0.65 + 0.35','Verified parents\n+ prefix guards','Refined Top 10\noriginal passages'];
 const fills=[C.teal,C.cyan,C.orange,C.teal,C.navy];
 xs.forEach((x,i)=>flowBox(s,'refine-step-'+i,labels[i],x,430,ws[i],fills[i],20));
 for(let i=0;i<4;i++)arrow(s,'refine-edge-'+i,xs[i],483,xs[i+1]+ws[i+1],483);
 text(s,'refinement-row-label','Current experimental refinement',50,375,950,30,22,C.teal,'left');
}

// 01: Hybrid RRF architecture.
{
const s=header('method_03_architecture','3','Architecture','Method 3 · Hybrid RRF',
 'The preserved core fuses vector and BM25 ranks. The lower layer is the latest experimental refinement.',
 ['tools/run_shared_retrieval.py: rank_method','src/occupational_fitness_rag/retrieval/fusion.py: reciprocal_rank_fusion','tools/refine_complex_retrieval.py: run','src/occupational_fitness_rag/evaluation/retrieval_refinement.py'],
 'Core: same-module dense cosine ranks from actual Nomic 768-dimensional vectors, Top20, and positive BM25 Top30. RRF adds 1/(60+rank) per engine and merges by original source ID. The comparison corpus contains 88 commercial/shared originals. Neither core nor refinement performs a fitness judgment.');
box(s,'query','Nurse note\n+ module',55,300,180,140,C.navy);
frame(s,'knowledge','Frozen guideline corpus',290,168,610,103);
box(s,'originals','88 original\npassages',305,194,270,61,C.grey,C.ink,21);
box(s,'embeddings','Nomic 768D\nsource vectors',595,194,290,61,C.grey,C.ink,21);
panel(s,'parallel-search','Parallel retrieval',290,318,255,162,C.pale);
box(s,'vector','Vector cosine · Top 20',302,365,231,46,C.cyan,C.white,21);
box(s,'sparse','BM25 · Top 30',302,422,231,45,C.cyan,C.white,21);
panel(s,'rank-fusion','Rank fusion',625,318,275,162);
box(s,'rrf','RRF\nk = 60',638,365,249,102,C.orange,C.white,26);
box(s,'baseline-output','Baseline Top 10\noriginal passages',1000,330,225,130,C.navy,C.white,23);
arrow(s,'query-to-search',235,388,290,388);arrow(s,'search-to-rrf',545,398,625,398);arrow(s,'rrf-to-originals',900,398,1000,398);
arrow(s,'corpus-to-search',418,271,418,318);
extension(s);
}

// 02: Hybrid RRF logic.
{
const s=header('method_03_logic_flow','3','Logic flow','Method 3 · Hybrid RRF',
 'Literal sentence views retain negation, uncertainty, subject and timing. They do not become verified clinical facts.',
 ['tools/run_shared_retrieval.py: rank_method','src/occupational_fitness_rag/retrieval/bm25.py: rank_bm25','src/occupational_fitness_rag/retrieval/fusion.py','src/occupational_fitness_rag/evaluation/retrieval_refinement.py: literal_facets, fuse_views, refine_ranking'],
 'Top row: preserved core. Bottom row: latest additional experimental variant. The original method anchor has weight0.65 and all additional sentence views share0.35. The full original-text footprints at1/3/5/10 are protected per query. No reference source IDs are read by ranking.');
 const xs=[50,290,530,800,1050],ws=[190,190,220,200,180];
 const labels=['Read whole note\n+ requested module','Filter corpus\nby module / licence','Parallel retrieval\nVector 20 + BM25 30','Fuse source ranks\nRRF, k = 60','Keep original\nTop 10'];
 xs.forEach((x,i)=>flowBox(s,'core-step-'+i,labels[i],x,190,ws[i],[C.navy,C.cyan,C.cyan,C.orange,C.teal][i]));
 for(let i=0;i<4;i++)arrow(s,'core-edge-'+i,xs[i]+ws[i],243,xs[i+1],243);
 commonFlowBottom(s);
 text(s,'formula','RRF(source) = Σ 1 / (60 + engine rank)',50,575,1120,40,24,C.ink,'left');
}

// 03: Local source/rule/section graph architecture.
{
const s=header('method_04_architecture','4','Architecture','Method 4 · Source graph-assisted retrieval',
 'This is a curated source / rule / section graph. It has no extracted entity graph or community-summary stage.',
 ['tools/run_shared_retrieval.py: rank_method(method="graph_local")','src/occupational_fitness_rag/retrieval/graph_local.py: expand_local_graph','configs/rules/austroads_commercial_v1.yaml','tools/refine_complex_retrieval.py: run'],
 'Seed score is0.8/sqrt(rank); title, evidence-text and query-to-rule terms add bounded direct scores. Edges connect shared-rule sources(weight0.70), catalogue references(0.90) and equal sections(0.22). One propagation uses0.12*edge_weight*direct_score. Candidate chunk score is max source score. The new variant widens the actual graph ranking before protected refinement.');
box(s,'query','Nurse note\n+ module',55,300,180,140,C.navy);
frame(s,'graph-inputs','Curated graph data',575,168,650,104);
box(s,'sources-sections','Original sources\n+ section links',590,194,290,62,C.grey,C.ink,21);
box(s,'rule-links','Rule-to-source\n+ catalogue links',900,194,310,62,C.grey,C.ink,21);
panel(s,'hybrid-seeds','Hybrid seeds',290,320,230,160,C.pale);
box(s,'seeds','Vector + BM25\nRRF seed ranks',302,365,206,102,C.cyan,C.white,23);
panel(s,'graph-scoring','Graph ranking',585,318,315,162);
box(s,'direct','Direct source / rule matches',597,363,291,46,C.blue,C.white,20);
box(s,'propagation','One-hop score propagation',597,421,291,46,C.orange,C.white,20);
box(s,'baseline-output','Baseline Top 10\noriginal passages',1000,330,225,130,C.navy,C.white,23);
arrow(s,'query-to-seeds',235,390,290,390);arrow(s,'seeds-to-graph',520,398,585,398);arrow(s,'graph-to-output',900,398,1000,398);arrow(s,'graph-data-to-rank',744,272,744,318);
extension(s);
}

// 04: Source graph logic.
{
const s=header('method_04_logic_flow','4','Logic flow','Method 4 · Source graph-assisted retrieval',
 'One propagation round: score(neighbour) += 0.12 × edge weight × direct source score. Clinical rule outcomes are not evaluated here.',
 ['src/occupational_fitness_rag/retrieval/graph_local.py: expand_local_graph','tools/run_shared_retrieval.py: rank_method','src/occupational_fitness_rag/evaluation/retrieval_refinement.py'],
 'The graph scorer searches all scoped source titles and original text, not only neighbouring seed nodes. Query-to-rule term matches provide navigational scores, not patient-rule truth. In the latest variant the graph ordering is widened to30 before literal-context refinement.');
const xs=[50,290,530,800,1050],ws=[190,190,220,200,180],labels=['Read note\n+ scoped corpus','Get hybrid\nRRF seeds','Score seed / title /\ntext / rule matches','Propagate over\ncurated graph edges','Sort source scores\n→ baseline Top 10'];
xs.forEach((x,i)=>flowBox(s,'graph-step-'+i,labels[i],x,190,ws[i],[C.navy,C.cyan,C.blue,C.orange,C.teal][i],20));
for(let i=0;i<4;i++)arrow(s,'graph-edge-'+i,xs[i]+ws[i],243,xs[i+1],243);
commonFlowBottom(s);
frame(s,'edge-types','Graph edge weights',290,574,940,60);
text(s,'edge-weight-values','Shared rule 0.70     |     Catalogue reference 0.90     |     Same section 0.22',310,590,900,30,21);
}

// 05: Criterion coverage v6 architecture.
{
const s=header('method_07_architecture','7','Architecture','Method 7 · Criterion coverage allocation V6',
 'Criterion coverage describes retrieved source metadata; it does not mean that a patient satisfies a clinical criterion.',
 ['src/occupational_fitness_rag/evaluation/planned_hybrid.py: plan_query, execute_plan','src/occupational_fitness_rag/evaluation/guarded_hybrid.py: rank_channels','src/occupational_fitness_rag/evaluation/prefix_allocation.py: allocate_prefix','tools/recover_complex_ten_adapters.py: repair','tools/refine_complex_retrieval.py: run'],
 'Original V6: verified facts become at most4 literal fact facets; original note remains an anchor. Search and at most2 lexical follow-ups are deduplicated per query/engine. Guarded v3 chooses10 from up to30, retaining the original RRF Top10 footprint. allocate_prefix exhaustively chooses5 among those10, maximizes corpus-typed criterion coverage, preserves the earlier Top5 typed-criterion floor, then retains the same10-source inventory. Latest refinement explicitly widens candidates beyond the oldTop10.');
box(s,'note','Original note',55,275,180,78,C.navy,C.white,23);
box(s,'facts','Frozen verified\nfacts + quotations',55,374,180,98,C.navy,C.white,21);
panel(s,'fact-planner','Fact-scoped plan',290,275,225,197,C.pale);
box(s,'fact-facets','≤4 fact facets\nvalues + exact quotes',302,324,201,134,C.cyan,C.white,23);
panel(s,'planned-search','Planned search',570,275,245,197);
box(s,'anchor-facet-search','Anchor + facet\nvector / BM25',582,320,221,78,C.blue,C.white,23);
box(s,'followups','Bounded BM25\nfollow-ups',582,410,221,48,C.orange,C.white,19);
panel(s,'v6-selection','Evidence selection',875,275,350,197);
box(s,'guarded-ten','Guarded frontier → Top 10',887,320,326,48,C.blue,C.white,22);
box(s,'exact-five','Exact Top 5 criterion prefix\nwithin the same 10 sources',887,382,326,76,C.orange,C.white,21);
frame(s,'corpus','Frozen knowledge',570,170,655,70);
text(s,'corpus-description','88 original passages + actual Nomic vectors',585,190,625,36,21);
poly(s,'note-to-facet-plan',[[235,314],[265,314],[265,355],[290,355]]);
poly(s,'facts-to-facet-plan',[[235,423],[265,423],[265,390],[290,390]]);
arrow(s,'facets-to-search',515,372,570,372);arrow(s,'search-to-v6',815,372,875,372);arrow(s,'corpus-to-search',692,240,692,275);
// The baseline Top10 is the output of the V6 selection module, not a diagnosis.
extension(s,{baselineX:1050,baselineBottom:472,inputPoints:[[55,314],[30,314],[30,610],[300,610]]});
}

// 06: V6 logical execution.
{
const s=header('method_07_logic_flow','7','Logic flow','Method 7 · Criterion coverage allocation V6',
 'Unknown facts remain unknown. The original V6 preserves its ten-source inventory; the latest refinement can use the wider measured frontier.',
 ['src/occupational_fitness_rag/evaluation/planned_hybrid.py','tools/run_scope88_shared_retrieval.py: deduplicate_channels','src/occupational_fitness_rag/evaluation/guarded_hybrid.py','src/occupational_fitness_rag/evaluation/prefix_allocation.py','tools/refine_complex_retrieval.py'],
 'Planner validates values and field names against the frozen query audit and checks every quotation is a literal substring of the note. Lexical coverage threshold0.60; at most2 keyword follow-ups; one bounded pass. No free-form inferred facts are used. MMR output in an older planning helper is not the selected V6 ranking; deduplicated measured channels feed guarded allocation and exact prefix selection.');
const xs=[50,360,670,980],w=250;
const top=['Read frozen note\n+ verified facts','Validate values / quotes\n→ ≤4 fact facets','Search note + facets\nvector / BM25','Inspect facet coverage\nthreshold = 0.60'];
top.forEach((v,i)=>flowBox(s,'v6-top-'+i,v,xs[i],178,w,[C.navy,C.cyan,C.blue,C.teal][i],21,99));
for(let i=0;i<3;i++)arrow(s,'v6-t-edge-'+i,xs[i]+w,227,xs[i+1],227);
arrow(s,'v6-followup-down',1105,277,1105,350);
const row=['Exact five-source prefix\nretain criterion floor','Candidate budget 30\n→ guarded Top 10','Deduplicate identical\nquery / engine views','If coverage <0.60:\n≤2 BM25 follow-ups'];
row.forEach((v,i)=>flowBox(s,'v6-middle-'+i,v,xs[i],350,w,[C.orange,C.teal,C.blue,C.orange][i],21,99));
for(let i=3;i>0;i--)arrow(s,'v6-middle-edge-'+i,xs[i],399,xs[i-1]+w,399);
arrow(s,'v6-return-down',175,449,175,538);
const xb=[50,360,670,1000],wb=[250,250,250,230],bottom=['Preserved core\nTop 10 originals','Widen frontier +\nliteral sentence views','Protected allocation\nprefixes 1 / 3 / 5 / 10','Refined Top 10\noriginal passages'];
bottom.forEach((v,i)=>flowBox(s,'v6-bottom-'+i,v,xb[i],538,wb[i],[C.navy,C.cyan,C.teal,C.navy][i],21,92));
for(let i=0;i<3;i++)arrow(s,'v6-bottom-edge-'+i,xb[i]+wb[i],584,xb[i+1],584);
}

// 07: Native Neo4j frontier architecture.
{
const s=header('method_09_architecture','9','Architecture','Method 9 · Neo4j frontier and criterion transfer',
 'Original native Neo4j searches are preserved. The latest refinement replays their recorded response frontier; it makes no new native calls.',
 ['tools/complex_native_worker.py: neo','tools/run_neo4j_strategies.py: GRAPH_QUERY','src/occupational_fitness_rag/evaluation/neo4j_strategies.py: native_rrf, rank','src/occupational_fitness_rag/evaluation/neo4j_criterion_transfer.py: transfer','tools/refine_complex_retrieval.py: run'],
 'Native SDK1.22.0: VectorRetriever Top30 and scoped Neo4j fulltext Top30; native per-engine ranks fuse withk60. Original local RRF Top20 supplies Cypher seeds. Actual containment and explicit section-reference edges return same-module originals with text hashes. Guarded graph ranking then frontier criterion transfer retains oldTop10 source coverage and Top5 typed-criterion coverage. This is a literal source graph, not an LLM-generated medical knowledge graph.');
box(s,'note','Whole note\n+ module',45,285,170,132,C.navy,C.white,23);
box(s,'rrf-seeds','Original RRF\nTop 20 seeds',45,438,170,58,C.blue,C.white,19);
frame(s,'native-index','Frozen Neo4j source index',285,170,940,79);
text(s,'index-data','Original text hashes + Nomic vectors + literal source / section edges',302,194,906,40,22);
panel(s,'native-search','Native retrieval',275,300,250,190,C.pale);
box(s,'neo-vector','VectorRetriever · Top 30',287,346,226,54,C.cyan,C.white,20);
box(s,'neo-fulltext','Fulltext search · Top 30',287,412,226,62,C.cyan,C.white,20);
panel(s,'graph-support','Graph support',585,300,290,190);
box(s,'native-fusion','Native RRF + literal edges',597,346,266,54,C.blue,C.white,20);
box(s,'graph-guard','Query prior + graph support\ncoverage-guarded ranking',597,412,266,62,C.orange,C.white,20);
panel(s,'criterion-transfer','Criterion transfer',940,300,285,190);
box(s,'native-frontier','Actual response frontier',952,346,261,54,C.blue,C.white,20);
box(s,'neo-criterion-prefix','Feasible Top 10\n+ exact criterion prefix',952,412,261,62,C.orange,C.white,21);
arrow(s,'query-to-native',215,358,275,358);arrow(s,'native-to-graph',525,395,585,395);arrow(s,'graph-to-transfer',875,395,940,395);
arrow(s,'index-to-native',400,249,400,300);
arrow(s,'index-to-literal-edges',730,249,730,300);
arrow(s,'note-to-original-rrf',130,417,130,438);
poly(s,'rrf-seeds-to-cypher',[[215,467],[245,467],[245,520],[555,520],[555,440],[585,440]],C.arrow,7);
extension(s,{baselineX:1090,baselineBottom:490,inputPoints:[[45,351],[20,351],[20,610],[300,610]],replay:true});
}

// 08: Native Neo4j logic.
{
const s=header('method_09_logic_flow','9','Logic flow','Method 9 · Neo4j frontier and criterion transfer',
 'Cypher follows only complete literal containment and explicit section references. Candidate source IDs and text hashes remain auditable.',
 ['tools/complex_native_worker.py: neo','tools/neo4j_extension_worker.py: lexical_query','tools/run_neo4j_strategies.py: GRAPH_QUERY','src/occupational_fitness_rag/evaluation/neo4j_strategies.py','src/occupational_fitness_rag/evaluation/neo4j_criterion_transfer.py'],
 'The five upper stages describe the preserved original native run. The lower chain transfers source allocation across actual response IDs, not expected answers. The current refinement uses a frozen native trace. Additional joint-prefix search for7/9 was a separate follow-up, not a native engine call.');
const xs=[50,290,530,800,1050],ws=[190,190,220,200,180],top=['Validate original\ntext / vector hashes','Native vector + fulltext\nTop 30 per engine','Fuse native ranks\nRRF, k = 60','Cypher paths from\noriginal RRF Top 20','Coverage-guarded\ngraph ranking'];
top.forEach((v,i)=>flowBox(s,'neo-step-'+i,v,xs[i],190,ws[i],[C.navy,C.cyan,C.orange,C.blue,C.teal][i],20));
for(let i=0;i<4;i++)arrow(s,'neo-core-edge-'+i,xs[i]+ws[i],243,xs[i+1],243);
arrow(s,'neo-frontier-down',1140,296,1140,430);
const xb=[1050,800,550,300,50],wb=[180,200,200,200,200],labels=['Union actual\nresponse frontier','Feasible Top 10\ncriterion coverage','Exact Top 5\ncriterion floor','Replay candidates\n+ protected refinement','Refined Top 10\noriginal passages'];
labels.forEach((v,i)=>flowBox(s,'neo-bottom-'+i,v,xb[i],430,wb[i],[C.cyan,C.orange,C.orange,C.teal,C.navy][i],20));
for(let i=0;i<4;i++)arrow(s,'neo-lower-edge-'+i,xb[i],483,xb[i+1]+wb[i+1],483);
frame(s,'native-boundary','Execution boundary',290,581,940,54);
text(s,'native-boundary-text','Native retrieval: original run     |     Current optimization: frozen frontier replay',308,594,904,31,20);
}

// 09: PageIndex and RRF architecture.
{
const s=header('method_10_architecture','10','Architecture','Method 10 · PageIndex and RRF predicate navigation',
 'A first-party navigator uses an actual PageIndex tree and local Qwen. Its summaries and branch labels never replace original guideline text.',
 ['tools/complex_native_worker.py: tree','tools/pageindex_extension_worker.py: map_native_tree, request_body','tools/run_scope88_tree.py: ranking_body, call','tools/refine_complex_retrieval.py: run'],
 'Original run: PageIndex0.4.5 frozen native tree and source mapping; Qwen3.5 4B selects at most3 branches, then ranks complete original leaves with predicate/negation/time instructions. Original RRF Top20 adds seed branches. Whole candidate payload is limited to20000 bytes. Strict selected node count ismin(10,available). The latest experiment replays the measured leaf inventory; it does not call native PageIndex chat or rerun Qwen navigation.');
box(s,'note','Whole note\n+ module',55,300,180,140,C.navy,C.white,23);
frame(s,'tree-index','Tree index and navigation model',290,168,935,103);
box(s,'tree-mapping','Branch / leaf IDs\n→ original source mapping',305,194,430,62,C.grey,C.ink,21);
box(s,'local-nav-model','Local Qwen3.5 4B\nOllama navigation',755,194,455,62,C.grey,C.ink,21);
panel(s,'navigation','Branch navigation',290,318,265,162,C.pale);
box(s,'qwen-branches','Qwen branch selection\n≤3 branch IDs',302,364,241,103,C.cyan,C.white,22);
panel(s,'original-ranking','Original-text ranking',625,318,300,162);
box(s,'branch-union','Add original RRF Top 20\nseed branches',637,362,276,46,C.blue,C.white,20);
box(s,'predicate-ranking','Qwen predicate ranking\nwhole original passages',637,420,276,47,C.orange,C.white,20);
box(s,'baseline-output','Strict ID validation\n→ baseline Top 10',1000,330,225,130,C.navy,C.white,23);
arrow(s,'note-to-navigation',235,390,290,390);arrow(s,'navigation-to-ranking',555,398,625,398);arrow(s,'ranking-to-source-ids',925,398,1000,398);arrow(s,'tree-to-branches',422,271,422,318);arrow(s,'model-to-ranker',775,271,775,318);
extension(s,{replay:true});
}

// 10: Tree/predicate logic.
{
const s=header('method_10_logic_flow','10','Logic flow','Method 10 · PageIndex and RRF predicate navigation',
 'Qwen ranking considers documented predicates, negation and temporal state. Native tree IDs are mapped back to unchanged original passages.',
 ['tools/complex_native_worker.py: tree','tools/run_scope88_tree.py: ranking_body, normalized_branch, call','tools/run_pageindex_strict_cardinality.py: parse_strict','tools/pageindex_extension_worker.py: request_body'],
 'Two original local Qwen calls per scope: branches and predicate-aware original ranking. Branch IDs are validated/deduplicated. Leaf output must use known IDs and exactlymin(10,available) items. Invalid/failed calls are retained and not silently replaced. The current refinement makes zero new native navigation calls.');
const xs=[50,290,530,800,1050],ws=[190,190,220,200,180],labels=['Validate native tree\n+ source mapping','Qwen selects\n≤3 branch IDs','Union branches with\nRRF Top 20 seeds','Collect whole originals\n≤20,000 UTF-8 bytes','Qwen ranks conditions,\nnegation and timing'];
labels.forEach((v,i)=>flowBox(s,'tree-step-'+i,v,xs[i],190,ws[i],[C.navy,C.cyan,C.blue,C.teal,C.orange][i],20));
for(let i=0;i<4;i++)arrow(s,'tree-upper-edge-'+i,xs[i]+ws[i],243,xs[i+1],243);
arrow(s,'tree-validator-down',1140,296,1140,430);
const xb=[1050,800,550,300,50],wb=[180,200,200,200,200],bottom=['Validate known IDs\n+ exact item count','Map leaf IDs to\noriginal source IDs','Baseline Top 10\nmin(10, available)','Replay leaf candidates\n+ protected refinement','Refined Top 10\noriginal evidence'];
bottom.forEach((v,i)=>flowBox(s,'tree-bottom-'+i,v,xb[i],430,wb[i],[C.orange,C.cyan,C.navy,C.teal,C.navy][i],20));
for(let i=0;i<4;i++)arrow(s,'tree-lower-edge-'+i,xb[i],483,xb[i+1]+wb[i+1],483);
arrow(s,'invalid-output-branch',1140,536,1140,578);
box(s,'failed-record','Invalid output\n→ retain failure',1030,578,200,57,C.cream,C.ink,19);
text(s,'tree-execution-note','Original run: real PageIndex tree + 2 local Qwen calls per scope.\nLatest refinement: frozen leaf candidates; no new native navigation calls.',50,576,920,60,20,C.outline,'left');
}

// 11: Exact common refinement implementation, kept out of baseline claims.
{
const s=header('shared_refinement','3 / 4 / 7 / 9 / 10','Shared refinement logic','Current experiment · Protected evidence allocation',
 'Reference labels are opened only after ranking. This layer returns evidence; it does not decide fitness to drive.',
 ['tools/refine_complex_retrieval.py: prepare, run','src/occupational_fitness_rag/evaluation/retrieval_refinement.py: literal_facets, fuse_views, literal_parent_closure, refine_ranking','tools/report_complex_refinement.py: packet_replay','src/occupational_fitness_rag/evaluation/retrieval_prefix_search.py: joint_prefix'],
 'Input note and scope are frozen across methods. Sentence views preserve verbatim uncertainty, subject and timing. Real local Nomic embeddings and BM25 searches are recorded. Deduplicate repeated query/engine views; original-method anchor weight0.65; all additional views share0.35. Literal parent containment is complete same-page text, not a generated summary. Parent support inherits0.95 times strongest measured child support when otherwise absent. At most32 strict local improvements protect full source footprints at1/3/5/10. Corpus criterion/all-original coverage is the objective, not clinical relevance or truth. Case packet replay independently uses5 whole sources/9000 serialized bytes without truncation or rank6 refill. Supplementary joint Top5 search for7/9 checked26410318 combinations with no ranking changes; it is not part of the native retrievers.');
const xs=[50,350,650,950],w=280,labels=['Frozen note + module\noriginal method frontier','Select ≤6 complete\nverbatim module sentences','Actual Nomic + BM25\nrank each sentence view','Weighted RRF\nanchor 0.65 / views 0.35'];
labels.forEach((v,i)=>flowBox(s,'shared-top-'+i,v,xs[i],184,w,[C.navy,C.cyan,C.blue,C.orange][i],21,106));
for(let i=0;i<3;i++)arrow(s,'shared-top-edge-'+i,xs[i]+w,237,xs[i+1],237);
arrow(s,'shared-turn',1090,290,1090,422);
const lower=['Case packet replay\n5 originals / 9,000 bytes','Refined Top 10 originals\nIDs + page / section / text','Best-improvement allocation\nprotect ranks 1 / 3 / 5 / 10','Verify same-page\ncomplete parent passages'];
lower.forEach((v,i)=>flowBox(s,'shared-bottom-'+i,v,xs[i],422,w,[C.pale,C.navy,C.teal,C.orange][i],21,106));
for(let i=3;i>0;i--)arrow(s,'shared-bottom-edge-'+i,xs[i],475,xs[i-1]+w,475);
frame(s,'joint-experiment','Supplementary test for methods 7 and 9',350,578,880,56);
text(s,'joint-description','Joint five-source selection: same candidate pool, same coverage floors',366,590,848,33,21);
}

// 12: Compact provenance appendix.
{
const s=header('code_map','3 / 4 / 7 / 9 / 10','Implementation map','Code references for the five methods',
 'Architecture content is derived from these first-party implementations; the supplied PDF contributes visual style only.',
 ['tools/run_shared_retrieval.py','src/occupational_fitness_rag/retrieval/graph_local.py','src/occupational_fitness_rag/evaluation/prefix_allocation.py','src/occupational_fitness_rag/evaluation/neo4j_criterion_transfer.py','tools/complex_native_worker.py','tools/run_scope88_tree.py','tools/refine_complex_retrieval.py','src/occupational_fitness_rag/evaluation/retrieval_refinement.py'],
 'Full repository-relative paths and content hashes are stored in source_manifest.json. Original corpus has88 commercial/shared units. The234-note run contains357 module scopes. Current7/9/10 helpers must not be described as automatic production replacements. This deck includes10 method-specific diagrams plus2 explanatory appendices.');
const entries=[
 ['3 · Hybrid RRF','tools/run_shared_retrieval.py :: rank_method()\nretrieval/fusion.py :: reciprocal_rank_fusion()'],
 ['4 · Source graph','retrieval/graph_local.py :: expand_local_graph()\nSources + rule links + same-section neighbours'],
 ['7 · Criterion V6','evaluation/planned_hybrid.py + guarded_hybrid.py\nevaluation/prefix_allocation.py :: allocate_prefix()'],
 ['9 · Neo4j frontier','tools/complex_native_worker.py :: neo()\nevaluation/neo4j_strategies.py + neo4j_criterion_transfer.py'],
 ['10 · PageIndex + RRF','tools/complex_native_worker.py :: tree()\ntools/run_scope88_tree.py :: ranking_body(), call()']
];
entries.forEach(([label,files],i)=>{const y=171+i*78;box(s,'method-label-'+i,label,55,y,255,62,i%2?C.teal:C.cyan,C.white,23);box(s,'method-files-'+i,files,335,y,890,62,C.grey,C.ink,20);arrow(s,'method-file-edge-'+i,310,y+31,335,y+31);});
frame(s,'refinement-files','Latest shared refinement',55,589,1170,57);
text(s,'shared-code-map','tools/refine_complex_retrieval.py  →  evaluation/retrieval_refinement.py',72,602,1136,33,22);
}

// Pin the exact inspected implementation without modifying any source or result.
const files=[...new Set(inventory.flatMap(s=>s.sources).map(s=>s.split(': ')[0]).filter(s=>s.endsWith('.py')||s.endsWith('.yaml')))];
const actualFiles=[];
for(let file of files){
 if(!file.startsWith('src/')&&file.startsWith('evaluation/'))file='src/occupational_fitness_rag/'+file;
 try{const data=await fs.readFile(path.join(project,file));actualFiles.push({file,sha256:crypto.createHash('sha256').update(data).digest('hex')});}catch{throw new Error('Missing code provenance: '+file);}
}
const reference=process.env.RAG_DIAGRAM_STYLE_PDF || process.argv[2];
if(!reference)throw new Error('Set RAG_DIAGRAM_STYLE_PDF to the supplied style-reference PDF. Only page 4 is used visually.');
const referenceHash=crypto.createHash('sha256').update(await fs.readFile(reference)).digest('hex');
await fs.writeFile(path.join(work,'source_manifest.json'),JSON.stringify({reference_style_page:4,reference_sha256:referenceHash,reference_content_used:false,palette:C,font:'Calibri bold',slide_size_css_px:[W,H],slides:inventory,source_files:actualFiles,diagram_count:10,appendices:2},null,2));

for(const [i,s] of deck.slides.items.entries()){
 const name=inventory[i].name;
 const png=await deck.export({slide:s,format:'png',scale:1.5});
 await fs.writeFile(path.join(work,'output/figures',name+'.png'),new Uint8Array(await png.arrayBuffer()));
 const layout=await s.export({format:'layout'});
 await fs.writeFile(path.join(work,'build',name+'.layout.json'),await layout.text());
 console.log('Rendered '+name);
}
const candidate=path.join(work,'build/candidate.pptx');
await (await PresentationFile.exportPptx(deck)).save(candidate);
// PDF export is performed by the installed Office document converter in
// export_pdf.ps1, preserving native Calibri and vector shapes.
const finalPath=process.env.RAG_DIAGRAM_FINAL_PATH || path.join(work,'output/rag_methods_architecture_and_logic.pptx');
if(process.env.FINALIZE==='1'){
 const result=await finalizePresentation({workspaceDir:work,candidatePath:candidate,finalPath,
  pythonExecutable:path.join(runtime,'python/python.exe'),
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
  explicitTotalSlideCount:12,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'reference',families:['Calibri'],referencePath:reference,referenceSha256:referenceHash},
  verifyArtifactToolImport:true,receiptPath:path.join(work,'build/final_validation.json')});
 console.log(JSON.stringify(result));
}
console.log('Native editable draft: '+candidate);
