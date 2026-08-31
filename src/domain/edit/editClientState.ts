export type EditSourceMode = "PROJECT_TASK" | "STANDALONE_UPLOAD";
export type EditExecutionMode = "AUTO" | "MANUAL";
export type EditInspectorTab = "CLIP"|"API"|"VOICE"|"AUDIO"|"LIPSYNC"|"SUBTITLE"|"EVALUATION"|"VERSION"|"OUTPUT";
export type EditListItem = { ref:string; label:string };

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
  page_state_uid: string|null;
  current_stage_uid: string|null;
  current_stage_phase: string|null;
  current_stage_score: number|null;
  current_error_uid: string|null;
  preview_uri: string|null;
  final_preview_uri: string|null;
  values: Readonly<Record<string,string>>;
  lists: Readonly<Record<string,readonly EditListItem[]>>;
  gate_state: Readonly<Record<string, boolean>>;
};

export const EMPTY_EDIT_RESOLVED_CONTEXT: EditResolvedContext = {
  project_id:null,topic_id:null,task_id:null,locked_blueprint_ref:null,production_package_ref:null,input_manifest_ref:null,input_fingerprint:null,
  working_draft_ref:null,editing_run_id:null,voice_run_id:null,saved_edit_version_id:null,output_version_id:null,dialogue_timing_binding_ref:null,
  page_state_uid:null,current_stage_uid:null,current_stage_phase:null,current_stage_score:null,current_error_uid:null,preview_uri:null,final_preview_uri:null,
  values:{},lists:{},gate_state:{},
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
  selected_track_ref: string|null;
  selected_clip_ref: string|null;
  correction_scope: unknown|null;
  correction_instruction: string;
  subtitles_visible: boolean;
  audio_monitor: string|null;
  draft_dirty: boolean;
  busy_action: string|null;
  active_view_action: string|null;
  last_action_uid: string|null;
  last_runtime_result: string|null;
};

export const INITIAL_EDIT_CLIENT_STATE: EditClientState = {
  source_mode:"PROJECT_TASK",execution_mode:"AUTO",resolved:{...EMPTY_EDIT_RESOLVED_CONTEXT},playhead:null,range_in:null,range_out:null,
  playback_rate:1,playing:false,loop:false,preview_muted:false,preview_volume:1,snap:false,zoom:1,inspector_tab:"CLIP",media_search:"",
  media_type_filter:null,selected_media_ref:null,selected_issue_ref:null,selected_version_ref:null,selected_track_ref:null,selected_clip_ref:null,
  correction_scope:null,correction_instruction:"",subtitles_visible:true,audio_monitor:null,draft_dirty:false,busy_action:null,active_view_action:null,
  last_action_uid:null,last_runtime_result:null,
};

export type EditClientAction =
  |{type:"SOURCE_MODE";value:EditSourceMode}
  |{type:"EXECUTION_MODE";value:EditExecutionMode}
  |{type:"BIND_RESOLVED_CONTEXT";value:EditResolvedContext}
  |{type:"CLEAR_RESOLVED_CONTEXT"}
  |{type:"PLAY"}|{type:"PAUSE"}|{type:"SEEK";value:unknown}|{type:"RANGE_IN";value:unknown}|{type:"RANGE_OUT";value:unknown}|{type:"RANGE_CLEAR"}|{type:"RATE";value:EditClientState["playback_rate"]}
  |{type:"LOOP"}|{type:"MUTE"}|{type:"PREVIEW_VOLUME";value:number}|{type:"SNAP"}|{type:"ZOOM_IN"}|{type:"ZOOM_OUT"}|{type:"ZOOM_FIT"}
  |{type:"INSPECTOR_TAB";value:EditInspectorTab}|{type:"MEDIA_SEARCH";value:string}|{type:"MEDIA_FILTER";value:string|null}|{type:"MEDIA_SELECT";value:string|null}
  |{type:"ISSUE_SELECT";value:string|null}|{type:"VERSION_SELECT";value:string|null}|{type:"TRACK_SELECT";value:string|null}|{type:"CLIP_SELECT";value:string|null}
  |{type:"CORRECTION_SCOPE";value:unknown}|{type:"CORRECTION_INSTRUCTION";value:string}|{type:"SUBTITLE_TOGGLE"}|{type:"AUDIO_MONITOR";value:string|null}
  |{type:"BUSY";value:string|null}|{type:"VIEW_ACTION";action_uid:string}|{type:"LOCAL_ACTION";action_uid:string;dirty?:boolean;result?:string}
  |{type:"RUNTIME_RESULT";action_uid:string;result:string|null};

function clearTransient(state: EditClientState): EditClientState {
  return {
    ...state,resolved:{...EMPTY_EDIT_RESOLVED_CONTEXT},playhead:null,range_in:null,range_out:null,playing:false,selected_media_ref:null,
    selected_issue_ref:null,selected_version_ref:null,selected_track_ref:null,selected_clip_ref:null,correction_scope:null,correction_instruction:"",
    draft_dirty:false,busy_action:null,active_view_action:null,last_action_uid:null,last_runtime_result:null,
  };
}

export function reduceEditClientState(state: EditClientState, action: EditClientAction): EditClientState {
  switch(action.type){
    case"SOURCE_MODE":return{...clearTransient(state),source_mode:action.value};
    case"EXECUTION_MODE":return{...state,execution_mode:action.value,last_action_uid:"EDIT-01-ACT-EXECUTION-MODE-SET"};
    case"BIND_RESOLVED_CONTEXT":return{...state,resolved:{...action.value,values:{...action.value.values},lists:{...action.value.lists},gate_state:{...action.value.gate_state}},draft_dirty:action.value.page_state_uid==="EDIT-01-ST-PAGE-EVAL_REQUIRED"};
    case"CLEAR_RESOLVED_CONTEXT":return{...state,resolved:{...EMPTY_EDIT_RESOLVED_CONTEXT},playing:false,range_in:null,range_out:null};
    case"PLAY":return{...state,playing:true,last_action_uid:"EDIT-01-ACT-PLAY"};case"PAUSE":return{...state,playing:false,last_action_uid:"EDIT-01-ACT-PAUSE"};case"SEEK":return{...state,playhead:action.value,last_action_uid:"EDIT-01-ACT-SEEK-TIMECODE"};
    case"RANGE_IN":return{...state,range_in:action.value,last_action_uid:"EDIT-01-ACT-RANGE-SET-IN"};case"RANGE_OUT":return{...state,range_out:action.value,last_action_uid:"EDIT-01-ACT-RANGE-SET-OUT"};case"RANGE_CLEAR":return{...state,range_in:null,range_out:null,loop:false,last_action_uid:"EDIT-01-ACT-RANGE-CLEAR"};
    case"RATE":return{...state,playback_rate:action.value,last_action_uid:"EDIT-01-ACT-PLAYBACK-RATE"};case"LOOP":return{...state,loop:!state.loop,last_action_uid:"EDIT-01-ACT-LOOP-TOGGLE"};case"MUTE":return{...state,preview_muted:!state.preview_muted,last_action_uid:"EDIT-01-ACT-UI-PREVIEW-MUTE"};
    case"PREVIEW_VOLUME":return{...state,preview_volume:Math.max(0,Math.min(1,action.value)),last_action_uid:"EDIT-01-ACT-UI-PREVIEW-VOLUME"};case"SNAP":return{...state,snap:!state.snap,last_action_uid:"EDIT-01-ACT-SNAP-TOGGLE"};
    case"ZOOM_IN":return{...state,zoom:Math.min(16,state.zoom*1.25),last_action_uid:"EDIT-01-ACT-UI-ZOOM-IN"};case"ZOOM_OUT":return{...state,zoom:Math.max(.125,state.zoom/1.25),last_action_uid:"EDIT-01-ACT-UI-ZOOM-OUT"};case"ZOOM_FIT":return{...state,zoom:1,last_action_uid:"EDIT-01-ACT-UI-ZOOM-FIT"};
    case"INSPECTOR_TAB":return{...state,inspector_tab:action.value,last_action_uid:`EDIT-01-ACT-INSPECTOR-${action.value}`};case"MEDIA_SEARCH":return{...state,media_search:action.value,last_action_uid:"EDIT-01-ACT-UI-MEDIA-FILTER"};case"MEDIA_FILTER":return{...state,media_type_filter:action.value,last_action_uid:"EDIT-01-ACT-UI-MEDIA-FILTER"};
    case"MEDIA_SELECT":return{...state,selected_media_ref:action.value,last_action_uid:"EDIT-01-ACT-MEDIA-SELECT"};case"ISSUE_SELECT":return{...state,selected_issue_ref:action.value};case"VERSION_SELECT":return{...state,selected_version_ref:action.value};
    case"TRACK_SELECT":return{...state,selected_track_ref:action.value};case"CLIP_SELECT":return{...state,selected_clip_ref:action.value};case"CORRECTION_SCOPE":return{...state,correction_scope:action.value};case"CORRECTION_INSTRUCTION":return{...state,correction_instruction:action.value};
    case"SUBTITLE_TOGGLE":return{...state,subtitles_visible:!state.subtitles_visible,last_action_uid:"EDIT-01-ACT-UI-SUBTITLE-TOGGLE"};case"AUDIO_MONITOR":return{...state,audio_monitor:action.value,last_action_uid:"EDIT-01-ACT-UI-AUDIO-MONITOR"};
    case"BUSY":return{...state,busy_action:action.value};
    case"VIEW_ACTION":return{...state,active_view_action:action.action_uid,last_action_uid:action.action_uid,last_runtime_result:`VIEW:${action.action_uid}`};
    case"LOCAL_ACTION":return{...state,last_action_uid:action.action_uid,last_runtime_result:action.result??`LOCAL:${action.action_uid}`,draft_dirty:action.dirty?true:state.draft_dirty,resolved:action.dirty?{...state.resolved,page_state_uid:"EDIT-01-ST-PAGE-EVAL_REQUIRED"}:state.resolved};
    case"RUNTIME_RESULT":return{...state,last_action_uid:action.action_uid,last_runtime_result:action.result};
  }
}
