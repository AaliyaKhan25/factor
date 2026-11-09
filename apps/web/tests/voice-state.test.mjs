import test from "node:test";
import assert from "node:assert/strict";
import { RecordingStateMachine } from "../src/lib/voice-state.mjs";

test("silence does not stop capture before speech is detected", () => {
  const state = new RecordingStateMachine();
  for (let i = 0; i < 80; i++) assert.equal(state.update(0, 100), "continue");
});

test("speech resets the silence timer and five seconds of silence ends the clip", () => {
  const state = new RecordingStateMachine();
  assert.equal(state.update(0.08, 100), "continue");
  for (let i = 0; i < 49; i++) assert.equal(state.update(0, 100), "continue");
  assert.equal(state.update(0.1, 100), "continue");
  for (let i = 0; i < 49; i++) assert.equal(state.update(0, 100), "continue");
  assert.equal(state.update(0, 100), "silence");
});

test("the 30 second cap wins even while speech continues", () => {
  const state = new RecordingStateMachine();
  for (let i = 0; i < 299; i++) assert.equal(state.update(0.08, 100), "continue");
  assert.equal(state.update(0.08, 100), "limit");
});
