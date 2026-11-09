export class RecordingStateMachine {
  update(rms: number, frameMs: number): "continue" | "silence" | "limit";
}
