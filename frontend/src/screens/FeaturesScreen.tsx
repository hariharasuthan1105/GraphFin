import React, { useEffect, useState, useMemo } from "react";
import { api } from "../api/client";
import { useApp } from "../context/AppContext";
import { Table, Column } from "../components/ui/Table";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { formatNumber, formatCurrency } from "../utils/formatters";
import { FeatureSchemaResponse, UserFeatures } from "../types/api";

export const FeaturesScreen: React.FC = () => {
  const { datasetId, setActiveNav, setSelectedNodeId, datasetCurrency } = useApp();

  const [schema, setSchema] = useState<FeatureSchemaResponse | null>(null);
  const [users, setUsers] = useState<UserFeatures[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [searchUserId, setSearchUserId] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const [sortKey, setSortKey] = useState<string>("user_id");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Load feature schema dynamically on mount
  useEffect(() => {
    api
      .getFeatureSchema()
      .then((s) => setSchema(s))
      .catch((err) => console.warn("Could not fetch feature schema:", err));
  }, []);

  // Load users feature data when datasetId or page changes
  useEffect(() => {
    if (!datasetId) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    api
      .getUserAnalytics(datasetId, {
        limit: pageSize,
        offset: page * pageSize,
        userId: searchUserId.trim() || undefined,
      })
      .then((resp) => {
        if (!isMounted) return;
        setUsers(resp.users);
        setTotalUsers(resp.total_users);
        setIsLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || "Failed to load user features.");
        setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [datasetId, page, searchUserId]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortOrder("desc");
    }
  };

  // Sort data locally for the loaded page
  const sortedUsers = useMemo(() => {
    const list = [...users];
    list.sort((a: any, b: any) => {
      let va = a[sortKey];
      let vb = b[sortKey];

      if (typeof va === "string") {
        return sortOrder === "asc"
          ? va.localeCompare(vb)
          : vb.localeCompare(va);
      }

      va = va ?? 0;
      vb = vb ?? 0;
      return sortOrder === "asc" ? va - vb : vb - va;
    });
    return list;
  }, [users, sortKey, sortOrder]);

  // Build columns dynamically from schema.features
  const dynamicColumns: Column<UserFeatures>[] = useMemo(() => {
    const cols: Column<UserFeatures>[] = [
      {
        key: "user_id",
        header: "User ID",
        mono: true,
        sortable: true,
        render: (row) => (
          <button
            onClick={() => {
              setSelectedNodeId(row.user_id);
              setActiveNav("graph");
            }}
            className="font-mono text-text-primary hover:text-accent-primary hover:underline text-left"
            title="Inspect in graph"
          >
            {row.user_id}
          </button>
        ),
      },
    ];

    if (schema?.features) {
      schema.features.forEach((featName) => {
        // Format label from snake_case
        const label = featName
          .split("_")
          .map((w, idx) => (idx === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w))
          .join(" ");

        cols.push({
          key: featName,
          header: label,
          tooltip: `Feature: ${featName}`,
          align: "right",
          mono: true,
          sortable: true,
          render: (row: any) => {
            const val = row[featName];
            if (val === undefined || val === null) return "—";

            if (featName.includes("amount") || featName.includes("total_sent") || featName.includes("total_received") || featName.includes("net_flow") || featName.includes("weighted")) {
              return formatCurrency(val, datasetCurrency);
            }
            if (featName === "betweenness_centrality") {
              return val.toFixed(6);
            }
            if (Number.isInteger(val)) {
              return formatNumber(val, 0);
            }
            return formatNumber(val, 2);
          },
        });
      });
    }

    return cols;
  }, [schema, setSelectedNodeId, setActiveNav, datasetCurrency]);

  if (!datasetId) {
    return (
      <div className="h-[calc(100vh-8rem)] flex flex-col items-center justify-center text-center space-y-4">
        <div className="space-y-1">
          <h2 className="text-lg font-sans font-medium text-text-primary">
            No dataset selected
          </h2>
          <p className="text-sm font-sans text-text-secondary max-w-sm">
            Select or upload a dataset to inspect calculated structural, behavioral, and temporal features.
          </p>
        </div>
        <Button variant="primary" onClick={() => setActiveNav("datasets")}>
          Upload a dataset to begin
        </Button>
      </div>
    );
  }

  const totalPages = Math.ceil(totalUsers / pageSize);

  return (
    <div className="space-y-6 w-full text-left">
      {/* Header section */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-sans font-medium text-text-primary">
            Feature Matrix
          </h1>
          <p className="text-sm font-sans text-text-secondary mt-1">
            Fused structural (graph), behavioral (volume/flow), and temporal features dynamically retrieved from schema.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Input
            placeholder="Filter by user ID..."
            value={searchUserId}
            onChange={(e) => {
              setSearchUserId(e.target.value);
              setPage(0);
            }}
            mono
            className="w-48 text-xs py-1"
          />
        </div>
      </div>

      {error && (
        <div className="p-3 bg-[#2D1619] border border-[#521A1F] rounded text-xs font-sans text-status-suspicious">
          {error}
        </div>
      )}

      {/* Dynamic Data Table */}
      <Table
        columns={dynamicColumns}
        data={sortedUsers}
        sortKey={sortKey}
        sortOrder={sortOrder}
        onSort={handleSort}
        isLoading={isLoading}
        stickyFirstColumn={true}
        emptyMessage="No entities match the current query."
      />

      {/* Pagination Footer */}
      <div className="flex items-center justify-between text-xs font-sans text-text-secondary pt-2 border-t border-hairline">
        <span className="font-mono">
          Showing {users.length} of {totalUsers} entities
        </span>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={page === 0 || isLoading}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </Button>
          <span className="font-mono px-2 text-text-primary">
            Page {page + 1} of {Math.max(1, totalPages)}
          </span>
          <Button
            size="sm"
            variant="secondary"
            disabled={page + 1 >= totalPages || isLoading}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
};
