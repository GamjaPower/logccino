'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import { Activity, PieChart as PieIcon } from 'lucide-react';

interface ServiceStat {
  service: string;
  total_logs: number;
  error_count: number;
  error_rate_pct?: number;
  status?: string;
}

interface Props {
  services: ServiceStat[];
}

const COLORS = ['#10b981', '#f59e0b', '#ef4444'];

export function MetricsCharts({ services }: Props) {
  const chartData = services.map(s => ({
    name: s.service,
    total: s.total_logs,
    errors: s.error_count
  }));

  const totalLogs = services.reduce((acc, s) => acc + (s.total_logs || 0), 0);
  const totalErrors = services.reduce((acc, s) => acc + (s.error_count || 0), 0);
  const totalInfos = Math.max(0, totalLogs - totalErrors);

  const pieData = [
    { name: 'INFO', value: totalInfos, color: '#10b981' },
    { name: 'ERROR', value: totalErrors, color: '#ef4444' }
  ];

  return (
    <div className="flex-1 p-4 space-y-4 overflow-y-auto">
      {/* Service Distribution Bar Chart */}
      <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800">
        <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-purple-400" /> 서비스별 로그 볼륨 & 에러 건수
        </h4>
        <div className="h-44 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
              <YAxis stroke="#64748b" fontSize={10} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }}
              />
              <Bar dataKey="total" fill="#6366f1" name="총 로그" radius={[4, 4, 0, 0]} />
              <Bar dataKey="errors" fill="#ef4444" name="에러 건수" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Level Breakdown Pie Chart */}
      <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800">
        <h4 className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
          <PieIcon className="w-3.5 h-3.5 text-indigo-400" /> 로그 레벨 분포 (INFO vs ERROR)
        </h4>
        <div className="h-40 w-full flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={40}
                outerRadius={65}
                paddingAngle={4}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}
                labelLine={false}
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
