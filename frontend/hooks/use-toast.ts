// Minimal toast hook compatible with @radix-ui/react-toast
import * as React from "react";

export type ToastVariant = "default" | "destructive";

export interface ToastProps {
  id?: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

interface ToastState {
  toasts: Required<ToastProps>[];
}

type Action =
  | { type: "ADD"; toast: Required<ToastProps> }
  | { type: "REMOVE"; id: string };

const TOAST_LIMIT = 5;
const TOAST_REMOVE_DELAY = 1_000_000; // managed via duration

const listeners: ((state: ToastState) => void)[] = [];
let memoryState: ToastState = { toasts: [] };

function dispatch(action: Action) {
  if (action.type === "ADD") {
    memoryState = {
      toasts: [action.toast, ...memoryState.toasts].slice(0, TOAST_LIMIT),
    };
  } else {
    memoryState = {
      toasts: memoryState.toasts.filter((t) => t.id !== action.id),
    };
  }
  listeners.forEach((l) => l(memoryState));
}

let counter = 0;
function genId() {
  counter = (counter + 1) % Number.MAX_SAFE_INTEGER;
  return String(counter);
}

export function toast(props: ToastProps) {
  const id = props.id ?? genId();
  const duration = props.duration ?? 5000;

  dispatch({
    type: "ADD",
    toast: { id, title: props.title ?? "", description: props.description ?? "", variant: props.variant ?? "default", duration },
  });

  setTimeout(() => {
    dispatch({ type: "REMOVE", id });
  }, duration + 300);

  return { id };
}

export function useToast() {
  const [state, setState] = React.useState<ToastState>(memoryState);

  React.useEffect(() => {
    listeners.push(setState);
    return () => {
      const idx = listeners.indexOf(setState);
      if (idx > -1) listeners.splice(idx, 1);
    };
  }, []);

  return {
    toasts: state.toasts,
    toast,
    dismiss: (id: string) => dispatch({ type: "REMOVE", id }),
  };
}
