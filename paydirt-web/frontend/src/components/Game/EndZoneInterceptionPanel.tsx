interface EndZoneInterceptionData {
  pending_end_zone_interception_return_decision?: boolean;
  int_catch_depth?: number;
  int_catch_field_position?: string;
  interception_return_situation?: string;
  int_return_team?: string;
  description?: string;
}

interface EndZoneInterceptionPanelProps {
  endZoneData?: EndZoneInterceptionData | null;
  onDecision?: (attemptReturn: boolean) => void;
  disabled?: boolean;
}

/**
 * Show the engine-provided catch location, score and clock before return dice.
 * The panel never derives a result or a field position; it only relays the
 * pending decision returned by the core engine.
 */
const EndZoneInterceptionPanel = ({
  endZoneData,
  onDecision,
  disabled = false,
}: EndZoneInterceptionPanelProps) => {
  if (!endZoneData?.pending_end_zone_interception_return_decision) {
    return null;
  }

  const team = endZoneData.int_return_team || 'The defense';
  const depth = endZoneData.int_catch_depth ?? 0;
  const catchPosition = endZoneData.int_catch_field_position
    || (depth === 0 ? 'own goal line' : `own ${depth}-yard line`);

  return (
    <div className="bg-indigo-800 rounded-lg px-4 py-4 text-center border-2 border-indigo-400">
      <div className="text-xl font-bold text-white mb-2">END-ZONE INTERCEPTION!</div>
      <div className="text-white font-bold text-lg">
        {team} caught it at the {catchPosition}
      </div>
      <div className="text-blue-100 text-sm mt-1">
        {endZoneData.description || 'Choose before any return dice are rolled.'}
      </div>
      {endZoneData.interception_return_situation && (
        <div className="mt-2 rounded bg-gray-900/60 px-3 py-2 text-sm text-gray-200">
          {endZoneData.interception_return_situation}
        </div>
      )}

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <button
          onClick={() => onDecision?.(false)}
          disabled={disabled}
          className="px-6 py-3 rounded-lg font-bold bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-600 disabled:text-gray-400"
        >
          TAKE TOUCHBACK
        </button>
        <button
          onClick={() => onDecision?.(true)}
          disabled={disabled}
          className="px-6 py-3 rounded-lg font-bold bg-green-600 text-white hover:bg-green-700 disabled:bg-gray-600 disabled:text-gray-400"
        >
          ATTEMPT RETURN
        </button>
      </div>
      <div className="mt-3 text-xs text-gray-300">
        {depth === 0
          ? 'Catch at the goal line; end-zone depth counts against a return.'
          : `Catch ${depth} yard(s) deep; that depth counts against a return.`}
      </div>
    </div>
  );
};

export default EndZoneInterceptionPanel;
