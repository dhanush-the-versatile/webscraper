"use client";

import { useTheme } from "next-themes";
import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAnalytics } from "@/hooks/use-api";
import type { CountPoint } from "@/types/api";

/**
 * Chart theming follows the dataviz method: one validated hue per mode
 * (series-1 blue — passes lightness/chroma/contrast checks on both surfaces),
 * solid hairline grid one shade off the surface, muted axis ink, and a
 * table-view twin for every ranked chart.
 */
function useChartTheme() {
  const { resolvedTheme } = useTheme();
  const dark = resolvedTheme === "dark";
  return {
    series: dark ? "#3987e5" : "#2a78d6",
    seriesSoft: dark ? "rgba(57,135,229,0.18)" : "rgba(42,120,214,0.14)",
    grid: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.07)",
    axis: dark ? "#9b9aa3" : "#6b6a72",
  };
}

function ChartTooltip({
  active,
  payload,
  label,
  valueLabel,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
  valueLabel: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border bg-popover px-3 py-1.5 text-xs shadow-md">
      <p className="font-medium text-popover-foreground">{label}</p>
      <p className="text-muted-foreground">
        {valueLabel}: <span className="font-semibold text-popover-foreground">{payload[0].value}</span>
      </p>
    </div>
  );
}

function RankedBar({
  title,
  data,
  valueLabel,
  emptyHint,
}: {
  title: string;
  data: CountPoint[] | undefined;
  valueLabel: string;
  emptyHint: string;
}) {
  const theme = useChartTheme();
  const items = (data ?? []).slice(0, 8);
  const height = Math.max(180, items.length * 34 + 30);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">{emptyHint}</p>
        ) : (
          <Tabs defaultValue="chart">
            <TabsList className="h-8">
              <TabsTrigger value="chart" className="text-xs">
                Chart
              </TabsTrigger>
              <TabsTrigger value="table" className="text-xs">
                Table
              </TabsTrigger>
            </TabsList>
            <TabsContent value="chart">
              <ResponsiveContainer width="100%" height={height}>
                <BarChart data={items} layout="vertical" margin={{ left: 8, right: 24 }}>
                  <CartesianGrid horizontal={false} stroke={theme.grid} />
                  <XAxis
                    type="number"
                    tick={{ fill: theme.axis, fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={110}
                    tick={{ fill: theme.axis, fontSize: 12 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: theme.seriesSoft }}
                    content={<ChartTooltip valueLabel={valueLabel} />}
                  />
                  <Bar
                    dataKey="value"
                    fill={theme.series}
                    barSize={14}
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </TabsContent>
            <TabsContent value="table">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{title.replace("Top ", "")}</TableHead>
                    <TableHead className="w-24 text-right">{valueLabel}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.label}>
                      <TableCell>{item.label}</TableCell>
                      <TableCell className="text-right tabular-nums">{item.value}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const { data, isLoading } = useAnalytics(days);
  const theme = useChartTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const timeSeries = useMemo(
    () =>
      (data?.searches_over_time ?? []).map((point) => ({
        label: new Date(point.date).toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
        }),
        value: point.value,
      })),
    [data],
  );

  if (isLoading || !mounted) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-64 rounded-xl" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-72 rounded-xl" />
          <Skeleton className="h-72 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* single filter row scoping all charts below */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground">
            Sourcing activity and talent-pool composition.
          </p>
        </div>
        <Select value={String(days)} onValueChange={(value) => setDays(Number(value))}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">Last 7 days</SelectItem>
            <SelectItem value="30">Last 30 days</SelectItem>
            <SelectItem value="90">Last 90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Searches over time</CardTitle>
        </CardHeader>
        <CardContent>
          {timeSeries.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No searches in this period yet.
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={timeSeries} margin={{ left: -18, right: 8, top: 6 }}>
                <defs>
                  <linearGradient id="searchFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={theme.series} stopOpacity={0.25} />
                    <stop offset="100%" stopColor={theme.series} stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke={theme.grid} />
                <XAxis
                  dataKey="label"
                  tick={{ fill: theme.axis, fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fill: theme.axis, fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <Tooltip
                  cursor={{ stroke: theme.axis, strokeOpacity: 0.35 }}
                  content={<ChartTooltip valueLabel="Searches" />}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={theme.series}
                  strokeWidth={2}
                  fill="url(#searchFill)"
                  dot={false}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--tooltip-ring, white)" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <RankedBar
          title="Top skills in pool"
          data={data?.top_skills}
          valueLabel="Candidates"
          emptyHint="Skills appear once candidates are collected."
        />
        <RankedBar
          title="Top countries"
          data={data?.top_countries}
          valueLabel="Candidates"
          emptyHint="Locations appear once candidates are collected."
        />
        <RankedBar
          title="Candidates by source"
          data={data?.candidates_by_source}
          valueLabel="Candidates"
          emptyHint="Run a search to start collecting."
        />
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Match-score distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {(data?.score_distribution ?? []).every((bucket) => bucket.value === 0) ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Scores appear after your first completed search.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data?.score_distribution} margin={{ left: -18, right: 8 }}>
                  <CartesianGrid vertical={false} stroke={theme.grid} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: theme.axis, fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fill: theme.axis, fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ fill: theme.seriesSoft }}
                    content={<ChartTooltip valueLabel="Candidates" />}
                  />
                  <Bar
                    dataKey="value"
                    fill={theme.series}
                    barSize={28}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
