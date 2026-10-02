library ieee; use ieee.std_logic_1164.all;
entity g1 is port (s : in natural; a : in std_ulogic; q : out std_ulogic); end entity;
architecture x of g1 is begin
  u: entity work.sub generic map (N => s) port map (a => a, y => q);
end architecture;
