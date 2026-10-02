library ieee; use ieee.std_logic_1164.all;
entity g2 is port (a : in std_ulogic; q : out std_ulogic); end entity;
architecture x of g2 is begin
  u: entity work.sub port map (a, q);
end architecture;
