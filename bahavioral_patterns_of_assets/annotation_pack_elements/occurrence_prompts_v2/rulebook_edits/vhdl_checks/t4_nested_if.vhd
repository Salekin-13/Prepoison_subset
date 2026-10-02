library ieee; use ieee.std_logic_1164.all;
entity t4 is port (clk, rstn, en, d : in std_ulogic; q : out std_ulogic); end entity;
architecture a of t4 is
begin
  p: process (rstn, clk)
  begin
    if rstn = '0' then
      q <= '0';
    elsif rising_edge(clk) then
      if en = '1' then
        q <= d;
      else
        q <= '0';
      end if;
    end if;
  end process p;
end architecture;
