# Quasarr UI extraction (2026-08-23) — research-leaf findings

Raw consolidated findings from the three read-only research leaves over
`/tmp/quasarr-src` decompiled Avalonia views. Condensed for the browser-rebuild
waves; the build target lives in `docs/research/quasarr-ui-parity-spec.md`.

## Main window / shell
- Avalonia + ShadUI desktop window; ~37 SidebarItem constructions in
  MainWindow.cs (4606 lines, compiled-XAML so labels recovered from literals).
- Theme tokens observed as DynamicResource keys: PrimaryColor, MutedColor/Muted,
  CardBackgroundColor, BorderColor, GhostHoverColor, ForegroundColor,
  WindowBackgroundBrush, Lg/Md/XlCornerRadius, "Monospace" text class,
  SidebarBrandPanel, ChromeButton/WindowControlBox (custom min/max/close),
  ShellBorder, Caption. Dark shadcn-style look.
- Navigation: sidebar items → view instances (TasksView, WalletsView,
  ActivityLogView, SettingsView, ToolsView, TransfersView, GasCalculatorView,
  ContractMinterManagerView, OpenseaCheckerView, NftManagerView, ProxyManagerView,
  RpcManagerView). ViewModels mirror 1:1 (TasksViewModel etc.).

## Core views (facts extracted)
- TasksView/TasksViewModel: the core screen — task table with status pills and
  filters, task groups, start/pause/cancel, add-task dialog (AddMintTaskDialog),
  bulk edit (BulkEditTasksDialog), phase filter items.
- WalletsView: wallet table, groups/batches (NewWalletBatch/NewWalletGroup/
  MoveWalletsToGroup dialogs), import/export wallet dialogs, balance refresh.
- ActivityLogView + ActivityLogViewModel: leveled activity log.
- SettingsView: sections include CaptchaSettingsViewModel, OpenSeaApiSettings
  (credential pool + transport option), QuickTaskSettings, proxies, RPC endpoints.
- ToolsView + GasCalculatorView: utility tools; gas calculator standalone.

## Money-flow views
- TransfersView is a TAB HOST ONLY: two segments Disperse | Collect driven by
  IsDisperseActive/IsCollectActive; all logic in child VMs.
- DisperseViewModel: source wallet combo w/ search ("Search wallet or paste
  address..."), RPC picker, wallet-group picker, Native|ERC-20 segmented control
  (+ token address box + auto symbol), recipient rows (address+amount) +
  bulk "apply to all", total (F6) + count readouts, AvailableWalletItem
  {Id,Address,Alias,Balance,IsSelected} checkbox pool synced to recipients,
  Select All/Clear All, sort Default/Alias±/Balance±, refresh-balances spinner.
  CanExecute gate: source+RPC+≥1 recipient+!executing (+token addr if ERC-20).
- CollectViewModel: N→1 collection; collect-all-with-gas-reserve or fixed
  amount modes; per-wallet gas awareness.
- ContractMinterManagerViewModel: deployments list + delegation groups
  (ContractMinterDelegationGroupItem/WalletItem), deployment display states,
  verify/reconcile lifecycle (DeployRequest/VerificationRequest/
  ReconcileRequest interfaces), batch executions/jobs/attempts journal.
- OpenseaCheckerView + NftManagerView: listing checker; listing drafts with
  ListingDraftRow/ListingPricingFill pricing fills.
- Dialogs worth mirroring later: TransactionConfirmationDialog,
  SpeedUpGasDialog, RecoverWalletsDialog, ExportWalletsDialog.
- LoginWindow exists but NOT ported: Mint Room is loopback-local, no auth gate.

## Process note (what worked)
Three parallel read-only leaves (~9 min each): shell/chrome, core views,
money-flow views. Contract that worked: forbid writes, demand file-cited facts
only, allow "unclear" over speculation, cap output length, one ## section per
view. Parent consolidated into the spec file the same turn.

## Sidebar ground truth (leaf 1, MainWindow.cs line cites — 2026-08-23)
Sidebar control: ShadUI Sidebar, Width=240/MinWidth=56, Padding=8,
ItemIconContentSpacing=12, right border 1px on SidebarBackgroundColor. Items in a
StackPanel Spacing=4 (MainWindow.cs:2200). Each item: Command=NavigateCommand +
string route param (`dashboard`, `wallets`, `tasks`, `transfers`, `nft`, `rpc`,
`proxy`, `tools`), IsChecked OneWay ← Is{Page}Route, tooltip
Sidebar{Page}Tooltip right/+8px/200ms, FontAwesome icon, label from resx key.
Order + icons (MainWindow.cs lines):
1. Dashboard fa-chart-line (2201–2248) · 2. Wallets fa-wallet (2250–2296) ·
3. Tasks fa-list-check (2298–2344) · 4. Transfers fa-arrow-right-arrow-left
(2346–2392) · 5. NFT fa-image (2394–2440) · 6. RPC fa-server (2442–2488) ·
7. Proxy fa-network-wired (2490–2536) · 8. Tools fa-toolbox (2538–2584).
View resolution via global ViewLocator (App.cs:769). NOTE vs Mint Room's shell:
Quasarr has NO Rarity/OpenSea-Checker/NftManager sidebar entries and NO
CORE/MODULES/MONEY/SYSTEM grouping — our sections are an adaptation; RPC and
Proxy managers are Quasarr pages we haven't stubbed yet (candidates for SYSTEM).

## TasksView detail for the build wave (from TasksViewModel leaf)
- Layout: LEFT panel "Task Groups" list; RIGHT pane = selected group's table.
  Empty states: "Select a task group" / "No task groups yet".
- Group card (TaskGroupItem): DisplayName (40-char trunc+…), Name,
  ContractAddressShort `0x1234…abcd`, TotalTasks/SuccessCount/FailedCount;
  actions CopyContractAddress / EditTaskGroup / DeleteTaskGroup. OpenSea groups
  (ModuleId=="opensea") show drop-phase schedule (OpenSeaDropStageItem:
  DisplayLabel, StartTimeUtcDisplay, HasStartTime) with SetOpenSeaDropSchedule
  (sets selected tasks to stage start) + RefreshOpenSeaDropSchedule gated.
- Table columns (TaskItem): checkbox IsSelected (header two-way IsAllTasksSelected),
  Wallet (alias+address), ValueDisplay, Mode (Direct/Simulation/Spam/Trigger +
  "Interval: X ms/s"), GasDisplay ("Auto" | "max / priority"), Status pill
  (pastel bg/fg per status), Tx hash → OpenInExplorer, row buttons
  Toggle/Edit/SpeedUp/Delete.
