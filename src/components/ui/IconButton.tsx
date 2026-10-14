"use client";

import { Icon, type IconName } from "./Icon";

export function IconButton({
  uid,
  label,
  icon,
  onAct,
  disabled,
  className,
}: {
  uid: string;
  label: string;
  icon: IconName;
  onAct: (uid: string) => void;
  disabled: boolean;
  className: string;
}) {
  return (
    <button
      type="button"
      className={className}
      data-control-uid={uid}
      data-tip={label}
      aria-label={label}
      disabled={disabled}
      onClick={() => onAct(uid)}
    >
      <Icon name={icon} />
    </button>
  );
}
