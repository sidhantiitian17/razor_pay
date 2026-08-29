create schema if not exists private;

revoke all on function public.has_role(uuid, app_role) from authenticated;
revoke all on function public.is_recon_operator() from authenticated;

alter function public.has_role(uuid, app_role) set schema private;
alter function public.is_recon_operator() set schema private;

alter function private.has_role(uuid, app_role) set search_path = public;
alter function private.is_recon_operator() set search_path = public;

grant usage on schema private to authenticated, service_role;
grant execute on function private.has_role(uuid, app_role) to authenticated, service_role;
grant execute on function private.is_recon_operator() to authenticated, service_role;

revoke all on schema private from public, anon;
revoke all on function private.has_role(uuid, app_role) from public, anon;
revoke all on function private.is_recon_operator() from public, anon;