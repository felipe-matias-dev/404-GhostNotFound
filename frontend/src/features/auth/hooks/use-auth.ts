import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useEffect } from "react";
import { getSession, SESSION_KEY, signIn, signOut, type User } from "../api";
import { loginDestination } from "../profiles";

export function useSession() {
	const client = useQueryClient();
	return useQuery({
		queryKey: SESSION_KEY,
		queryFn: async () => {
			const user = await getSession();
			const previous = client.getQueryData<User | null>(SESSION_KEY);
			if (previous && previous.login !== user?.login) {
				await client.cancelQueries({
					predicate: (query) => query.queryKey[0] !== "auth",
				});
				client.removeQueries({
					predicate: (query) => query.queryKey[0] !== "auth",
				});
				client.getMutationCache().clear();
			}
			return user;
		},
		staleTime: 30_000,
		retry: false,
	});
}

export function useSessionExpiry() {
	const client = useQueryClient();
	useEffect(() => {
		function expire() {
			void client.cancelQueries();
			client.removeQueries({
				predicate: (query) => query.queryKey[0] !== "auth",
			});
			client.getMutationCache().clear();
			client.setQueryData(SESSION_KEY, null);
		}
		window.addEventListener("venergy:session-expired", expire);
		return () => window.removeEventListener("venergy:session-expired", expire);
	}, [client]);
}

export function useLogin() {
	const client = useQueryClient();
	const navigate = useNavigate();
	const search = useSearch({ strict: false });
	return useMutation({
		mutationFn: signIn,
		onSuccess: async (user) => {
			await client.cancelQueries();
			client.removeQueries({
				predicate: (query) => query.queryKey[0] !== "auth",
			});
			client.getMutationCache().clear();
			client.setQueryData(SESSION_KEY, user);
			await navigate({
				href: loginDestination(user.perfil, search.redirect),
				replace: true,
			});
		},
	});
}

export function useLogout() {
	const client = useQueryClient();
	const navigate = useNavigate();
	return useMutation({
		mutationFn: signOut,
		onSuccess: async () => {
			await client.cancelQueries();
			client.removeQueries({
				predicate: (query) => query.queryKey[0] !== "auth",
			});
			client.getMutationCache().clear();
			client.setQueryData(SESSION_KEY, null);
			await navigate({ to: "/login", replace: true });
		},
	});
}
