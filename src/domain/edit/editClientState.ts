export type EditSourceMode = "PROJECT_TASK" | "STANDALONE_UPLOAD";
export type EditExecutionMode = "AUTO" | "MANUAL";
export type EditInspectorTab = "CLIP"|"API"|"VOICE"|"AUDIO"|"LIPSYNC"|"SUBTITLE"|"EVALUATION"|"VERSION"|"OUTPUT";

export type EditResolvedContext = {
  project_id: string|null;
  topic_id: string|null;
  task_id: string|null;
  locked_blueprint_ref: string|null;
  production_package_ref: string|null;
  input_manifest_ref: string|null;
  input_fingerprint: string|null;
  working_draft_ref: string|null;
  editing_run_id: string|null;
  voice_run_id: string|null;
  saved_edit_version_id: string|null;
  output_version_id: string|null;
  dialogue_timing_binding_ref: string|null;
};

export const EMPTY_EDIT_RESOLVED_CONTEXT: EditResolvedContext = {
  project_id:null,topic_id:null,task_id:null,locked_blueprint_ref:null,production_package_ref:null,input_manifest_ref:null,input_fingerprint:null,
  working_draft_ref:null,editing_run_id:null,voice_run_id:null,saved_edit_version_id:null,output_version_id:null,dialogue_timing_binding_ref:null,
};

export type EditClientState = {
  source_mode: EditSourceMode;
  execution_mode: EditExecutionMode;
  resolved: EditResolvedContext;
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
  source_mode:"PROJECT_TASK",execution_mode:"AUTO",resolved:{...EMPTY_EDIT_RESOLVED_CONTEXT},playhead:null,range_in:null,range_out:null,
  playback_rate:1,playing:false,loop:false,preview_muted:false,preview_volume:1,snap:false,zoom:1,inspector_tab:"CLIP",media_search:"",
  media_type_filter:null,selected_media_ref:null,selected_issue_ref:null,selected_version_ref:null,correction_scope:null,correction_instruction:"",
  subtitles_visible:true,audio_monitor:null,
};

export type EditClientAction =
  |{type:"SOURCE_MODE";value:EditSourceMode}
  |{type:"EXECUTION_MODE";value:EditExecutionMode}
  |{type:"BIND_RESOLVED_CONTEXT";value:EditResolvedContext}
  |{type:"CLEAR_RESOLVED_CONTEXT"}
  |{type:"PLAY"}|{type:"PAUSE"}|{type:"SEEK";value:unknown}|{type:"RANGE_IN";value:unknown}|{type:"RANGE_OUT";value:unknown}|{type:"RANGE_CLEAR"}|{type:"RATE";value:EditClientState["playback_rate"]}
  |{type:"LOOP"}|{type:"MUTE"}|{type:"PREVIEW_VOLUME";value:number}|{type:"SNAP"}|{type:"ZOOM_IN"}|{type:"ZOOM_OUT"}|{type:"ZOOM_FIT"}
  |{type:"INSPECTOR_TAB";value:EditInspectorTab}|{type:"MEDIA_SEARCH";value:string}|{type:"MEDIA_FILTER";value:string|null}|{type:"MEDIA_SELECT";value:string|null}
  |{type:"ISSUE_SELECT";value:string|null}|{type:"VERSION_SELECT";value:string|null}|{type:"CORRECTION_SCOPE";value:unknown}|{type:"CORRECTION_INSTRUCTION";value:string}
  |{type:"SUBTITLE_TOGGLE"}|{type:"AUDIO_MONITOR";value:string|null};

function clearTransient(state: EditClientState): EditClientState {
  return {
    ...state,
    resolved:{...EMPTY_EDIT_RESOLVED_CONTEXT},
    playhead:null,range_in:null,range_out:null,playing:false,selected_media_ref:null,selected_issue_ref:null,selected_version_ref:null,
    correction_scope:null,correction_instruction:"",
  };
}

export function reduceEditClientState(state: EditClientState, action: EditClientAction): EditClientState {
  switch(action.type){
    case"SOURCE_MODE":return{...clearTransient(state),source_mode:action.value};
    case"EXECUTION_MODE":return{...state,execution_mode:action.value};
    case"BIND_RESOLVED_CONTEXT":return{...state,resolved:{...action.value}};
    case"CLEAR_RESOLVED_CONTEXT":return{...state,resolved:{...EMPTY_EDIT_RESOLVED_CONTEXT},playing:false,range_in:null,range_out:null};
    case"PLAY":return{...state,playing:true};
    case"PAUSE":return{...state,playing:false};
    case"SEEK":return{...state,playhead:action.value};
    case"RANGE_IN":return{...state,range_in:action.value};
    case"RANGE_OUT":return{...state,range_out:action.value};
    case"RANGE_CLEAR":return{...state,range_in:null,range_out:null,loop:false};
    case"RATE":return{...state,playback_rate:action.value};
    case"LOOP":return{...state,loop:!state.loop};
    case"MUTE":return{...state,preview_muted:!state.preview_muted};
    case"PREVIEW_VOLUME":return{...state,preview_volume:Math.max(0,Math.min(1,action.value))};
    case"SNAP":return{...state,snap:!state.snap};
    case"ZOOM_IN":return{...state,zoom:Math.min(16,state.zoom*1.25)};
    case"ZOOM_OUT":return{...state,zoom:Math.max(.125,state.zoom/1.25)};
    case"ZOOM_FIT":return{...state,zoom:1};
    case"INSPECTOR_TAB":return{...state,inspector_tab:action.value};
    case"MEDIA_SEARCH":return{...state,media_search:action.value};
    case"MEDIA_FILTER":return{...state,media_type_filter:action.value};
    case"MEDIA_SELECT":return{...state,selected_media_ref:action.value};
    case"ISSUE_SELECT":return{...state,selected_issue_ref:action.value};
    case"VERSION_SELECT":return{...state,selected_version_ref:action.value};
    case"CORRECTION_SCOPE":return{...state,correction_scope:action.value};
    case"CORRECTION_INSTRUCTION":return{...state,correction_instruction:action.value};
    case"SUBTITLE_TOGGLE":return{...state,subtitles_visible:!state.subtitles_visible};
    case"AUDIO_MONITOR":return{...state,audio_monitor:action.value};
  }
}
