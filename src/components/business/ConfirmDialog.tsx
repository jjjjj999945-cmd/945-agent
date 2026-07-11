type ConfirmDialogProps = {
  open: boolean;
  title: string;
  children: React.ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel,
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
          <button onClick={onConfirm}>{confirmLabel}</button>
          <button className="ghost" onClick={onCancel}>
            {cancelLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
