"use client";

import { useMemo, useState } from "react";
import Icon from "@/components/ui/Icon";
import { rupees } from "@/lib/format";

type DayPoint = {
  date: string;
  total_paise: number;
};

interface Props {
  daily: DayPoint[];
  onSelectDay?: (day: DayPoint) => void;
}

export default function InteractiveSalesChart({ daily, onSelectDay }: Props) {
  const [timeframe, setTimeframe] = useState<"7d" | "14d" | "28d">("28d");
  const [metricMode, setMetricMode] = useState<"daily" | "cumulative">("daily");
  const [hoveredDay, setHoveredDay] = useState<DayPoint | null>(null);
  const [selectedDay, setSelectedDay] = useState<DayPoint | null>(null);

  // Slice based on timeframe
  const activeData = useMemo(() => {
    const count = timeframe === "7d" ? 7 : timeframe === "14d" ? 14 : 28;
    const slice = daily.slice(-count);

    if (metricMode === "cumulative") {
      let run = 0;
      return slice.map((item) => {
        run += item.total_paise;
        return { ...item, total_paise: run, raw_daily: item.total_paise };
      });
    }
    return slice;
  }, [daily, timeframe, metricMode]);

  // Aggregate stats
  const { total, max, min, avg, peakDay, activeDays } = useMemo(() => {
    const rawSlice = daily.slice(-(timeframe === "7d" ? 7 : timeframe === "14d" ? 14 : 28));
    const sum = rawSlice.reduce((acc, curr) => acc + curr.total_paise, 0);
    const maximum = Math.max(...activeData.map((d) => d.total_paise), 1);
    const minimum = Math.min(...activeData.map((d) => d.total_paise));
    const average = Math.round(sum / (rawSlice.length || 1));
    const peak = rawSlice.reduce((prev, curr) => (curr.total_paise > prev.total_paise ? curr : prev), rawSlice[0] || { date: "", total_paise: 0 });
    const active = rawSlice.filter((d) => d.total_paise > 0).length;

    return { total: sum, max: maximum, min: minimum, avg: average, peakDay: peak, activeDays: active };
  }, [daily, activeData, timeframe]);

  // Format date labels
  const formatLabel = (dateStr: string) => {
    try {
      const d = new Date(dateStr + "T00:00:00");
      if (timeframe === "7d") {
        return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric" });
      }
      return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
    } catch {
      return dateStr;
    }
  };

  const formatFullDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr + "T00:00:00");
      return d.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    } catch {
      return dateStr;
    }
  };

  const avgHeightPercent = Math.min(Math.max((avg / max) * 100, 4), 96);

  return (
    <div className="space-y-4">
      {/* Top Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-soft text-brand-dark">
              <Icon name="chart" className="h-4 w-4" />
            </span>
            <h3 className="font-display text-lg font-bold text-ink">Sales Velocity & Volume</h3>
          </div>
          <p className="mt-0.5 text-xs text-stone-500">
            {timeframe === "7d" ? "Past 7 days performance" : timeframe === "14d" ? "Past 2 weeks performance" : "Past 4 weeks (28 days) performance"}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Mode Switcher */}
          <div className="flex rounded-xl bg-cream-dark p-1 text-xs font-semibold">
            <button
              onClick={() => setMetricMode("daily")}
              className={`rounded-lg px-2.5 py-1 transition-all ${
                metricMode === "daily" ? "bg-white text-ink shadow-sm" : "text-stone-600 hover:text-ink"
              }`}
            >
              Daily Bars
            </button>
            <button
              onClick={() => setMetricMode("cumulative")}
              className={`rounded-lg px-2.5 py-1 transition-all ${
                metricMode === "cumulative" ? "bg-white text-ink shadow-sm" : "text-stone-600 hover:text-ink"
              }`}
            >
              Cumulative Run
            </button>
          </div>

          {/* Timeframe Selector */}
          <div className="flex rounded-xl border border-line bg-white p-1 text-xs font-semibold">
            {(["7d", "14d", "28d"] as const).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`rounded-lg px-2.5 py-1 transition-all ${
                  timeframe === tf ? "bg-brand font-bold text-ink shadow-sm" : "text-stone-600 hover:bg-stone-50 hover:text-ink"
                }`}
              >
                {tf === "7d" ? "7 Days" : tf === "14d" ? "14 Days" : "28 Days"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Key Metric Snapshot Chips */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div className="rounded-xl border border-line bg-cream/40 p-2.5 transition-colors hover:bg-white hover:shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Total Period Sales</p>
          <p className="mt-1 font-display text-lg font-bold text-ink">{rupees(total)}</p>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-stone-500">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-dark" />
            <span>{activeData.length} days range</span>
          </div>
        </div>

        <div className="rounded-xl border border-line bg-cream/40 p-2.5 transition-colors hover:bg-white hover:shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Daily Average</p>
          <p className="mt-1 font-display text-lg font-bold text-ink">{rupees(avg)}</p>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-stone-500">
            <span className="text-stone-400">Target benchmark</span>
          </div>
        </div>

        <div className="rounded-xl border border-line bg-cream/40 p-2.5 transition-colors hover:bg-white hover:shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Peak Performance</p>
          <p className="mt-1 font-display text-lg font-bold text-emerald-800">{rupees(peakDay?.total_paise ?? 0)}</p>
          <div className="mt-1 flex items-center gap-1 text-[11px] text-stone-500 truncate">
            <span>{peakDay?.date ? formatLabel(peakDay.date) : "N/A"}</span>
          </div>
        </div>

        <div className="rounded-xl border border-line bg-cream/40 p-2.5 transition-colors hover:bg-white hover:shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-wider text-stone-500">Active Sales Days</p>
          <div className="mt-1 flex items-baseline gap-1.5">
            <span className="font-display text-lg font-bold text-ink">{activeDays}</span>
            <span className="text-xs text-stone-500">/ {activeData.length} days</span>
          </div>
          <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-stone-200">
            <div
              className="h-full rounded-full bg-brand"
              style={{ width: `${Math.round((activeDays / (activeData.length || 1)) * 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Main Bar Chart Container */}
      <div className="relative mt-2 rounded-2xl border border-line bg-cream/30 p-4 pt-6">
        {/* Average Benchmark Line (for daily mode) */}
        {metricMode === "daily" && avg > 0 && (
          <div
            className="pointer-events-none absolute inset-x-4 z-10 flex items-center border-t border-dashed border-stone-400/60"
            style={{ bottom: `calc(${avgHeightPercent}% + 2rem)` }}
          >
            <span className="ml-auto rounded-md bg-stone-100/90 px-1.5 py-0.5 text-[9px] font-semibold text-stone-600 shadow-sm backdrop-blur">
              Avg: {rupees(avg)}
            </span>
          </div>
        )}

        {/* Hover Tooltip Overlay */}
        {hoveredDay && (
          <div className="pointer-events-none absolute -top-3 left-1/2 z-20 -translate-x-1/2 transform rounded-xl border border-line bg-ink px-3 py-2 text-white shadow-xl">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-brand" />
              <p className="text-xs font-semibold text-stone-200">{formatFullDate(hoveredDay.date)}</p>
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="font-display text-base font-bold text-white">{rupees(hoveredDay.total_paise)}</span>
              {hoveredDay.total_paise > 0 && (
                <span className="text-[10px] font-medium text-brand">
                  {Math.round((hoveredDay.total_paise / (total || 1)) * 100)}% of period
                </span>
              )}
            </div>
          </div>
        )}

        {/* Bar Visualization */}
        <div className="flex h-52 items-end gap-1 sm:gap-1.5">
          {activeData.map((x) => {
            const isHovered = hoveredDay?.date === x.date;
            const isSelected = selectedDay?.date === x.date;
            const isPeak = peakDay && peakDay.date === x.date && peakDay.total_paise > 0;
            const heightPercent = max > 0 ? Math.max((x.total_paise / max) * 100, x.total_paise > 0 ? 5 : 2) : 2;

            return (
              <div
                key={x.date}
                className="group relative flex flex-1 flex-col items-center justify-end h-full"
                onMouseEnter={() => setHoveredDay(x)}
                onMouseLeave={() => setHoveredDay(null)}
                onClick={() => {
                  setSelectedDay(x);
                  onSelectDay?.(x);
                }}
              >
                {/* Peak Day Star Indicator */}
                {isPeak && metricMode === "daily" && (
                  <div className="absolute -top-5 flex flex-col items-center animate-bounce">
                    <span className="grid h-4 w-4 place-items-center rounded-full bg-brand text-brand-dark shadow-xs">
                      <Icon name="star" className="h-2.5 w-2.5" />
                    </span>
                  </div>
                )}

                {/* The Bar Element */}
                <div
                  className={`w-full rounded-t-md transition-all duration-300 cursor-pointer ${
                    isSelected
                      ? "bg-brand-dark ring-2 ring-brand-dark ring-offset-1"
                      : isHovered
                      ? "bg-brand-dark brightness-110 shadow-glow"
                      : x.total_paise > 0
                      ? isPeak
                        ? "bg-brand hover:bg-brand-hover shadow-sm"
                        : "bg-brand/90 hover:bg-brand"
                      : "bg-stone-200/80 hover:bg-stone-300"
                  }`}
                  style={{
                    height: `${heightPercent}%`,
                  }}
                />

                {/* Day Labels - spaced dynamically */}
                <span
                  className={`mt-2 block truncate text-[9px] font-medium transition-colors ${
                    isHovered || isSelected ? "font-bold text-ink" : "text-stone-600"
                  } ${
                    timeframe === "28d"
                      ? "hidden sm:block text-[8px]"
                      : ""
                  }`}
                >
                  {timeframe === "7d"
                    ? formatLabel(x.date)
                    : timeframe === "14d"
                    ? formatLabel(x.date).split(" ")[0]
                    : formatLabel(x.date).split(" ")[0]}
                </span>
              </div>
            );
          })}
        </div>

        {/* Date bounds footer labels for 28-day view */}
        {timeframe === "28d" && activeData.length > 0 && (
          <div className="mt-2 flex items-center justify-between border-t border-line/50 pt-2 text-[10px] font-semibold text-stone-600">
            <span>{formatLabel(activeData[0].date)}</span>
            <span className="text-stone-600">Interactive 28-Day Timeline · Hover to Inspect</span>
            <span>{formatLabel(activeData[activeData.length - 1].date)}</span>
          </div>
        )}
      </div>

      {/* Selected Day Spotlight Card */}
      {selectedDay && (
        <div className="flex items-center justify-between rounded-xl border border-brand/50 bg-brand-soft/60 px-4 py-3 transition-all animate-fadeIn">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand text-brand-dark">
              <Icon name="calendar" className="h-5 w-5" />
            </span>
            <div>
              <p className="text-xs font-semibold text-brand-dark">Day Focus: {formatFullDate(selectedDay.date)}</p>
              <p className="font-display text-base font-bold text-ink">
                {rupees(selectedDay.total_paise)} revenue generated
              </p>
            </div>
          </div>
          <button
            onClick={() => setSelectedDay(null)}
            className="rounded-lg p-1 text-brand-dark hover:bg-brand/40"
            title="Clear selection"
          >
            <Icon name="close" className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
