import type { MouseEvent, ReactNode } from "react";

type XpWindowProps = {
  title: string;
  titleId?: string;
  heading?: boolean;
  controls?: ReactNode;
  children: ReactNode;
  status?: string;
  className?: string;
  root?: "main" | "div";
  role?: string;
  ariaModal?: boolean;
  ariaLabelledBy?: string;
  onClick?: (event: MouseEvent<HTMLElement>) => void;
};

export function XpWindow({
  title,
  titleId,
  heading = false,
  controls,
  children,
  status,
  className,
  root = "main",
  role,
  ariaModal,
  ariaLabelledBy,
  onClick,
}: XpWindowProps) {
  const Root = root === "div" ? "div" : "main";
  const classes = ["window", className].filter(Boolean).join(" ");

  return (
    <Root
      className={classes}
      role={role}
      aria-modal={ariaModal}
      aria-labelledby={ariaLabelledBy}
      onClick={onClick}
    >
      <div className="title-bar">
        {heading ? (
          <h1 className="title-bar-text" id={titleId}>
            {title}
          </h1>
        ) : (
          <div className="title-bar-text" id={titleId}>
            {title}
          </div>
        )}
        {controls ? <div className="title-bar-controls">{controls}</div> : null}
      </div>
      <div className="window-body">{children}</div>
      {status !== undefined ? (
        <div className="status-bar">
          <p className="status-bar-field">{status}</p>
        </div>
      ) : null}
    </Root>
  );
}
