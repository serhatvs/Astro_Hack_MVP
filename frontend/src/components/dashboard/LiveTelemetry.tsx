import { useEffect, useState } from "react";

import { useI18n } from "@/lib/i18n";

const LiveTelemetry = () => {
  const { t } = useI18n();
  const [temp, setTemp] = useState(-64.2);
  const [pressure, setPressure] = useState(101.3);
  const [radiationElevated, setRadiationElevated] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setTemp((previous) => +(previous + (Math.random() - 0.5) * 0.8).toFixed(1));
      setPressure((previous) => +(previous + (Math.random() - 0.5) * 0.3).toFixed(1));
      setRadiationElevated(Math.random() <= 0.05);
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  const radiation = radiationElevated ? t("telemetry_elevated") : t("telemetry_nominal");

  return (
    <div className="glass-panel min-w-0 overflow-hidden p-3 space-y-2">
      <h3 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
        {t("telemetry_title")}
      </h3>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <TelemetryItem label={t("telemetry_temp")} value={`${temp} C`} />
        <TelemetryItem label={t("telemetry_rad")} value={radiation} alert={radiationElevated} />
        <TelemetryItem label={t("telemetry_pressure")} value={`${pressure} kPa`} />
      </div>
    </div>
  );
};

const TelemetryItem = ({ label, value, alert = false }: { label: string; value: string; alert?: boolean }) => (
  <div className="text-center">
    <p className="text-[9px] font-mono uppercase text-muted-foreground tracking-wider">{label}</p>
    <p className={`text-sm font-mono font-bold ${alert ? "text-neon-orange" : "neon-text-cyan"}`}>{value}</p>
  </div>
);

export default LiveTelemetry;
