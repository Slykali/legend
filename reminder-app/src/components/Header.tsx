import { BellIcon, BellOffIcon, PlusIcon } from "./Icons";
import { Logo } from "./Illustration";
import { Button, IconButton } from "./ui/Button";

export interface HeaderProps {
  permission: NotificationPermission | "unsupported";
  onRequestPermission: () => void;
  onAdd: () => void;
}

function NotificationControl({
  permission,
  onRequestPermission,
}: Pick<HeaderProps, "permission" | "onRequestPermission">) {
  if (permission === "unsupported") return null;

  if (permission === "granted") {
    return (
      <IconButton label="Alerts are on" tone="ok">
        <BellIcon className="h-5 w-5" />
      </IconButton>
    );
  }

  if (permission === "denied") {
    return (
      <IconButton
        label="Alerts are blocked. Allow notifications for this site in your browser settings."
        aria-disabled="true"
        className="opacity-70"
      >
        <BellOffIcon className="h-5 w-5 text-muted" />
      </IconButton>
    );
  }

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={onRequestPermission}
      aria-label="Enable alerts"
      title="Get a notification when a reminder is due"
      className="gap-1.5"
    >
      <BellIcon className="h-4 w-4 shrink-0" />
      <span className="sm:hidden">Alerts</span>
      <span className="hidden sm:inline">Enable alerts</span>
    </Button>
  );
}

export function Header({ permission, onRequestPermission, onAdd }: HeaderProps) {
  return (
    <header
      className="sticky top-0 z-30 border-b border-line/70 bg-app/80 backdrop-blur-md supports-[backdrop-filter]:bg-app/65"
      style={{ paddingTop: "env(safe-area-inset-top)" }}
    >
      <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-3 py-3 pl-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))]">
        <div className="flex min-w-0 items-center gap-2.5">
          <Logo className="h-8 w-8 shrink-0" />
          <h1 className="truncate text-lg font-semibold tracking-tight text-fg">Remind</h1>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <NotificationControl permission={permission} onRequestPermission={onRequestPermission} />
          <Button variant="primary" size="sm" onClick={onAdd} className="gap-1.5" aria-label="New reminder">
            <PlusIcon className="h-4 w-4 shrink-0" />
            <span>New</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
