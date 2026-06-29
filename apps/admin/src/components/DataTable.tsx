export function DataTable({
  columns,
  rows,
  empty = "No records",
}: {
  columns: string[];
  rows: Array<Array<string | number>>;
  empty?: string;
}) {
  if (rows.length === 0) return <p className="p-6 text-center text-sm text-muted">{empty}</p>;
  return (
    <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-primary/10 bg-gray-bg/50">
          <tr>
            {columns.map((c) => (
              <th key={c} className="px-4 py-3 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-primary/5">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
