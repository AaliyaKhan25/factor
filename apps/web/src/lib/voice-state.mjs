/** Silence starts after speech; the 30 second ceiling applies from capture start. */
export class RecordingStateMachine {
  #heardSpeech = false;
  #silentMs = 0;
  #elapsedMs = 0;

  update(rms, frameMs) {
    this.#elapsedMs += frameMs;
    if (this.#elapsedMs >= 30_000) return "limit";
    if (rms >= 0.025) {
      this.#heardSpeech = true;
      this.#silentMs = 0;
    } else if (this.#heardSpeech) {
      this.#silentMs += frameMs;
    }
    return this.#heardSpeech && this.#silentMs >= 5_000 ? "silence" : "continue";
  }
}
