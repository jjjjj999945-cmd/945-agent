type ConfirmDialogProps = {
  open: boolean;
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  confirmDisabled?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel,
  confirmDisabled = false,
  onConfirm,
  onCancel
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="confirm-backdrop" role="presentation">
      <section aria-modal="true" className="confirm-dialog" role="dialog">
        <h2>{title}</h2>
        <div className="confirm-content">{children}</div>
        <div className="button-row">
          <button disabled={confirmDisabled} onClick={onConfirm} type="button">
            {confirmLabel}
          </button>
          <button className="ghost" onClick={onCancel} type="button">
            {cancelLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
