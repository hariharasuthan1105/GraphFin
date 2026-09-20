import React, { useRef, useState, useEffect, useCallback } from "react";

export interface Column<T> {
  key: string;
  header: string;
  tooltip?: string;
  render?: (row: T, index: number) => React.ReactNode;
  sortable?: boolean;
  align?: "left" | "right" | "center";
  mono?: boolean;
}

export interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  sortKey?: string;
  sortOrder?: "asc" | "desc";
  onSort?: (key: string) => void;
  isLoading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  stickyFirstColumn?: boolean;
  className?: string;
}

export function Table<T extends Record<string, any>>({
  columns,
  data,
  sortKey,
  sortOrder,
  onSort,
  isLoading = false,
  emptyMessage = "No records found.",
  onRowClick,
  stickyFirstColumn = false,
  className = "",
}: TableProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasOverflowRight, setHasOverflowRight] = useState(false);

  // Check horizontal overflow status
  const checkOverflow = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const isOverflowing = el.scrollWidth > el.clientWidth;
    const isAtEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 4;
    setHasOverflowRight(isOverflowing && !isAtEnd);
  }, []);

  useEffect(() => {
    checkOverflow();
    const el = containerRef.current;
    if (!el) return;

    el.addEventListener("scroll", checkOverflow, { passive: true });
    window.addEventListener("resize", checkOverflow);

    return () => {
      el.removeEventListener("scroll", checkOverflow);
      window.removeEventListener("resize", checkOverflow);
    };
  }, [data, columns, checkOverflow]);

  return (
    <div className={`relative w-full border border-hairline bg-surface ${className}`}>
      {/* Scrollable table container */}
      <div ref={containerRef} className="w-full overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm font-sans">
          <thead>
            <tr className="border-b border-hairline bg-surface-raised/70 select-none">
              {columns.map((col, colIdx) => {
                const isCurrentSort = sortKey === col.key;
                const isSticky = stickyFirstColumn && colIdx === 0;
                const alignment =
                  col.align === "right"
                    ? "text-right"
                    : col.align === "center"
                    ? "text-center"
                    : "text-left";

                return (
                  <th
                    key={col.key}
                    onClick={() => col.sortable && onSort && onSort(col.key)}
                    className={`px-3.5 py-2.5 text-xs font-medium text-text-secondary ${alignment} ${
                      col.sortable ? "cursor-pointer hover:text-text-primary transition-colors" : ""
                    } ${
                      isSticky
                        ? "sticky left-0 bg-surface-raised z-20 border-r border-hairline shadow-[1px_0_0_0_#232B33]"
                        : ""
                    }`}
                    title={col.tooltip}
                  >
                    <div
                      className={`inline-flex items-center gap-1.5 ${
                        col.align === "right" ? "justify-end" : ""
                      }`}
                    >
                      <span>{col.header}</span>
                      {col.sortable && isCurrentSort && (
                        <span className="font-mono text-accent-primary">
                          {sortOrder === "asc" ? "▲" : "▼"}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {isLoading ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-sm text-text-tertiary"
                >
                  Loading table data...
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-sm text-text-tertiary"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row, idx) => (
                <tr
                  key={idx}
                  onClick={() => onRowClick && onRowClick(row)}
                  className={`group transition-colors ${
                    onRowClick
                      ? "cursor-pointer hover:bg-surface-raised"
                      : "hover:bg-surface-raised/40"
                  }`}
                >
                  {columns.map((col, colIdx) => {
                    const isSticky = stickyFirstColumn && colIdx === 0;
                    const alignment =
                      col.align === "right"
                        ? "text-right"
                        : col.align === "center"
                        ? "text-center"
                        : "text-left";
                    const fontClass = col.mono ? "font-mono" : "font-sans";

                    return (
                      <td
                        key={col.key}
                        className={`px-3.5 py-2 text-sm text-text-primary ${alignment} ${fontClass} ${
                          isSticky
                            ? "sticky left-0 bg-surface group-hover:bg-surface-raised z-10 border-r border-hairline shadow-[1px_0_0_0_#232B33]"
                            : ""
                        }`}
                      >
                        {col.render ? col.render(row, idx) : row[col.key] ?? "—"}
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Right-edge overflow fade affordance (24px wide from transparent to canvas) */}
      {hasOverflowRight && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute top-0 right-0 bottom-0 w-6 bg-gradient-to-r from-transparent to-canvas transition-opacity duration-150"
        />
      )}
    </div>
  );
}
