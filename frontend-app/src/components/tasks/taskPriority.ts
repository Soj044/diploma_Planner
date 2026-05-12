export function priorityPillClass(priority: string | null | undefined): string {
  if (priority === "low") {
    return "is-priority-low";
  }
  if (priority === "medium") {
    return "is-priority-medium";
  }
  if (priority === "high") {
    return "is-priority-high";
  }
  if (priority === "critical") {
    return "is-priority-critical";
  }
  return "";
}
