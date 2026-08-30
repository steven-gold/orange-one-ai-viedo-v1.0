export type EditSourceMode = "PROJECT_TASK" | "STANDALONE_UPLOAD";
export type EditExecutionMode = "AUTO" | "MANUAL";
export type EditInspectorTab = "CLIP"|"API"|"VOICE"|"AUDIO"|"LIPSYNC"|"SUBTITLE"|"EVALUATION"|"VERSION"|"OUTPUT";
export type EditClientState = {
  source_mode: EditSourceMode;
  execution_mode: EditExecutionMode;
  project_ref: string|null;
  topic_ref: string|null;
  task_ref: string|null;
  playhead: unknown|null;
  range_in: unknown|null;
  range_out: unknown|null;
  playback_rate: 0.25|0.5|1|1.5|2;
  playing: boolean;
  loop: boolean;
  preview_muted: boolean;
  preview_volume: number;
  snap: boolean;
  zoom: number;
  inspector_tab: EditInspectorTab;
  media_search: string;
  media_type_filter: string|null;
  selected_media_ref: string|null;
  selected_issue_ref: string|null;
  selected_version_ref: string|null;
  correction_scope: unknown|null;
  correction_instruction: string;
  subtitles_visible: boolean;
  audio_monitor: string|null;
};
export const INITIAL_EDIT_CLIENT_STATE: EditClientState = {
  source_mode:"PROJECT_TASK",execution_mode:"AUTO",project_ref:null,topic_ref:null,task_ref:null,playhead:null,range_in:null,range_out:null,
  playback_rate:1,playing:false,loop:false,preview_muted:false,preview_volume:1,snap:false,zoom:1,inspector_tab:"CLIP",media_search:"",
  media_type_filter:null,selected_media_ref:null,selected_issue_ref:null,selected_version_ref:null,correction_scope:null,correction_instruction:"",
  subtitles_visible:true,audio_monitor:null
};
export type EditClientAction =
  |{type:"SOURCE_MODE";value:EditSourceMode}|{type:"EXECUTION_MODE";value:EditExecutionMode}|{type:"PROJECT";value:string|null}|{type:"TOPIC";value:string|null}|{type:"TASK";value:string|null}
  |{type:"PLAY"}|{type:"PAUSE"}|{type:"SEEK";value:unknown}|{type:"RANGE_IN";value:unknown}|{type:"RANGE_OUT";value:unknown}|{type:"RANGE_CLEAR"}|{type:"RATE";value:EditClientState["playback_rate"]}
  |{type:"LOOP"}|{type:"MUTE"}|{type:"PREVIEW_VOLUME";value:number}|{type:"SNAP"}|{type:"ZOOM_IN"}|{type:"ZOOM_OUT"}|{type:"ZOOM_FIT"}
  |{type:"INSPECTOR_TAB";value:EditInspectorTab}|{type:"MEDIA_SEARCH";value:string}|{type:"MEDIA_FILTER";value:string|null}|{type:"MEDIA_SELECT";value:string|null}
  |{type:"ISSUE_SELECT";value:string|null}|{type:"VERSION_SELECT";value:string|null}|{type:"CORRECTION_SCOPE";value:unknown}|{type:"CORRECTION_INSTRUCTION";value:string}
  |{type:"SUBTITLE_TOGGLE"}|{type:"AUDIO_MONITOR";value:string|null};
function resetContext(s:EditClientState):EditClientState{return{...s,project_ref:null,topic_ref:null,task_ref:null,playhead:null,range_in:null,range_out:null,playing:false,selected_media_ref:null,selected_issue_ref:null,selected_version_ref:null,correction_scope:null,correction_instruction:""};}
export function reduceEditClientState(s:EditClientState,a:EditClientAction):EditClientState{switch(a.type){
case"SOURCE_MODE":return{...resetContext(s),source_mode:a.value};case"EXECUTION_MODE":return{...s,execution_mode:a.value};case"PROJECT":return{...resetContext(s),source_mode:"PROJECT_TASK",project_ref:a.value};case"TOPIC":return{...s,topic_ref:a.value,task_ref:null,selected_issue_ref:null,correction_scope:null};case"TASK":return{...s,task_ref:a.value,selected_issue_ref:null,correction_scope:null};
case"PLAY":return{...s,playing:true};case"PAUSE":return{...s,playing:false};case"SEEK":return{...s,playhead:a.value};case"RANGE_IN":return{...s,range_in:a.value};case"RANGE_OUT":return{...s,range_out:a.value};case"RANGE_CLEAR":return{...s,range_in:null,range_out:null,loop:false};case"RATE":return{...s,playback_rate:a.value};case"LOOP":return{...s,loop:!s.loop};case"MUTE":return{...s,preview_muted:!s.preview_muted};case"PREVIEW_VOLUME":return{...s,preview_volume:Math.max(0,Math.min(1,a.value))};case"SNAP":return{...s,snap:!s.snap};case"ZOOM_IN":return{...s,zoom:Math.min(16,s.zoom*1.25)};case"ZOOM_OUT":return{...s,zoom:Math.max(.125,s.zoom/1.25)};case"ZOOM_FIT":return{...s,zoom:1};
case"INSPECTOR_TAB":return{...s,inspector_tab:a.value};case"MEDIA_SEARCH":return{...s,media_search:a.value};case"MEDIA_FILTER":return{...s,media_type_filter:a.value};case"MEDIA_SELECT":return{...s,selected_media_ref:a.value};case"ISSUE_SELECT":return{...s,selected_issue_ref:a.value};case"VERSION_SELECT":return{...s,selected_version_ref:a.value};case"CORRECTION_SCOPE":return{...s,correction_scope:a.value};case"CORRECTION_INSTRUCTION":return{...s,correction_instruction:a.value};case"SUBTITLE_TOGGLE":return{...s,subtitles_visible:!s.subtitles_visible};case"AUDIO_MONITOR":return{...s,audio_monitor:a.value};}}
