import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createLazyScreen } from "@porterchain/mobile-performance";
import { JobsScreen } from "../../screens/jobs/JobsScreen";
import { JobDetailScreen } from "../../screens/jobs/JobDetailScreen";
import { AssignmentQueueScreen } from "../../screens/jobs/AssignmentQueueScreen";
import type { JobsStackParamList } from "../types";

const PodScreen = createLazyScreen(() => import("../../screens/jobs/PodScreen"), "PodScreen");
const IncidentScreen = createLazyScreen(() => import("../../screens/jobs/IncidentScreen"), "IncidentScreen");

const Stack = createNativeStackNavigator<JobsStackParamList>();

export function JobsStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, freezeOnBlur: true }}>
      <Stack.Screen name="Jobs" component={JobsScreen} />
      <Stack.Screen name="JobDetail" component={JobDetailScreen} />
      <Stack.Screen name="AssignmentQueue" component={AssignmentQueueScreen} />
      <Stack.Screen name="Pod" component={PodScreen as never} />
      <Stack.Screen name="Incident" component={IncidentScreen as never} />
    </Stack.Navigator>
  );
}
