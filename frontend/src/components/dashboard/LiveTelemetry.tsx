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
    <div className="glass-panel min-w-0 overflow-hidden bg-muted/10 p-2.5 space-y-1.5">
      <h3 className="text-[9px] font-mono uppercase tracking-[0.22em] text-muted-foreground/80">
        {t("telemetry_title")}
      </h3>
      <div className="grid grid-cols-3 gap-2.5">
        <TelemetryItem label={t("telemetry_temp")} value={`${temp} C`} />
        <TelemetryItem label={t("telemetry_rad")} value={radiation} alert={radiationElevated} />
        <TelemetryItem label={t("telemetry_pressure")} value={`${pressure} kPa`} />
      </div>
    </div>
  );
};

const TelemetryItem = ({ label, value, alert = false }: { label: string; value: string; alert?: boolean }) => (
  <div className="text-center">
    <p className="text-[8px] font-mono uppercase text-muted-foreground/75 tracking-[0.18em]">{label}</p>
    <p className={`text-xs font-mono font-semibold ${alert ? "text-neon-orange" : "neon-text-cyan"}`}>{value}</p>
  </div>
);

export default LiveTelemetry;
