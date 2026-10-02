library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity k1 is port (clk : in std_ulogic; q : out std_ulogic); end entity;
architecture x of k1 is
  signal n : natural range 0 to 15;
  signal v : std_ulogic_vector(3 downto 0);
begin
  p: process (clk) begin
    if rising_edge(clk) then
      case n is
        when v'length => q <= '1';
        when 0 to v'high - 1 => q <= '0';
        when others => q <= '0';
      end case;
    end if;
  end process p;
end architecture;
