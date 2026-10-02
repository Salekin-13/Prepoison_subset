library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity d2 is port (a : in std_ulogic; q : out std_ulogic); end entity;
architecture x of d2 is begin
  b: block
    signal s_blk : std_ulogic;
  begin
    s_blk <= a; q <= s_blk;
  end block b;
end architecture;
