"use client";

import { Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { roleLabel } from "@/design/tokens";
import { useAccount } from "@/components/account-provider";
import { homeFor } from "@/components/role-gate";

export function AccountSwitcher() {
  const { users, userId, selectUser } = useAccount();
  const router = useRouter();
  const selected = users.find((user) => String(user.id) === userId);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className={buttonVariants({ variant: "outline" })}>
        {selected?.name ?? "Account"}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-48">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Account</DropdownMenuLabel>
          {users.map((user) => {
            const id = String(user.id);
            const active = id === userId;
            return (
              <DropdownMenuItem key={user.id} onClick={() => {
                  selectUser(id);
                  router.push(homeFor(user.role));
                }}>
                <span className="flex min-w-0 flex-1 flex-col">
                  <span>{user.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {roleLabel(user.role)}
                  </span>
                </span>
                {active ? <Check aria-hidden /> : null}
              </DropdownMenuItem>
            );
          })}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
