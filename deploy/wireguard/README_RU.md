# Corgi Edge WireGuard

Скрипт `provision-node.sh` подготавливает Linux-ноду WireGuard для Corgi Edge.

Перед production запуском:
1. установить `wireguard-tools`;
2. выполнить скрипт на выделенной ноде;
3. зарегистрировать ноду через `/api/admin/v16/nodes/register`;
4. настроить peer provisioning через секретный control-plane канал;
5. проверить health-check и failover;
6. включить `wg-quick@wg-corgi`.

Скрипт не включает сбор пользовательского трафика и не записывает payload VPN.
