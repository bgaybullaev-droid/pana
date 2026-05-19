import { useEffect, useState } from "react";
import {
	Stack,
	Table,
	Badge,
	Group,
	Pagination,
	Loader,
	Text,
	Button,
	SegmentedControl,
} from "@mantine/core";
import { useUnit } from "effector-react";

import {
	$feedbackQueue,
	fetchFeedbackQueueFx,
	handleFeedbackFx,
} from "../../model";

const CATEGORY_COLORS: Record<string, string> = {
	grammar: "blue",
	unnatural: "orange",
	factual: "red",
	too_long: "grape",
	too_short: "violet",
	other: "gray",
};

export function FeedbackTab() {
	const data = useUnit($feedbackQueue);
	const loading = useUnit(fetchFeedbackQueueFx.pending);
	const [handled, setHandled] = useState<"open" | "done">("open");
	const [page, setPage] = useState(1);

	useEffect(() => {
		void fetchFeedbackQueueFx({ handled: handled === "done", page });
	}, [handled, page]);

	const onHandle = async (id: string) => {
		await handleFeedbackFx(id);
		void fetchFeedbackQueueFx({ handled: handled === "done", page });
	};

	return (
		<Stack gap="md">
			<Group justify="space-between">
				<SegmentedControl
					data={[
						{ label: "Open", value: "open" },
						{ label: "Handled", value: "done" },
					]}
					value={handled}
					onChange={(v) => {
						setPage(1);
						setHandled(v as "open" | "done");
					}}
				/>
				{data && (
					<Text size="sm" c="dimmed">
						{data.total} total
					</Text>
				)}
			</Group>
			{loading || !data ? (
				<Loader />
			) : (
				<>
					<Table withTableBorder striped>
						<Table.Thead>
							<Table.Tr>
								<Table.Th>Received</Table.Th>
								<Table.Th>Category</Table.Th>
								<Table.Th>Comment</Table.Th>
								<Table.Th>Listing</Table.Th>
								<Table.Th />
							</Table.Tr>
						</Table.Thead>
						<Table.Tbody>
							{data.items.map((row) => (
								<Table.Tr key={row.id}>
									<Table.Td>{new Date(row.created_at).toLocaleString()}</Table.Td>
									<Table.Td>
										<Badge color={CATEGORY_COLORS[row.category] ?? "gray"}>
											{row.category}
										</Badge>
									</Table.Td>
									<Table.Td>
										<Text size="sm" lineClamp={3}>
											{row.comment ?? "—"}
										</Text>
									</Table.Td>
									<Table.Td>
										<Text size="xs" c="dimmed" style={{ wordBreak: "break-all" }}>
											{row.listing_id ?? "—"}
										</Text>
									</Table.Td>
									<Table.Td>
										{!row.handled && (
											<Button size="xs" variant="light" onClick={() => onHandle(row.id)}>
												Mark handled
											</Button>
										)}
									</Table.Td>
								</Table.Tr>
							))}
							{data.items.length === 0 && (
								<Table.Tr>
									<Table.Td colSpan={5}>
										<Text size="sm" c="dimmed" ta="center">
											Queue is empty.
										</Text>
									</Table.Td>
								</Table.Tr>
							)}
						</Table.Tbody>
					</Table>
					<Pagination
						value={page}
						onChange={setPage}
						total={Math.max(1, Math.ceil(data.total / 25))}
					/>
				</>
			)}
		</Stack>
	);
}
