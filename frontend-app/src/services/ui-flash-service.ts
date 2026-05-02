interface UiFlashMessage {
  kind: "success" | "error";
  text: string;
}

let currentFlash: UiFlashMessage | null = null;

export function setUiFlash(message: UiFlashMessage): void {
  currentFlash = message;
}

export function consumeUiFlash(): UiFlashMessage | null {
  const message = currentFlash;
  currentFlash = null;
  return message;
}
